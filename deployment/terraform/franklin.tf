#
# Security Group Resources
#
resource "aws_security_group" "alb" {
  name   = "sg${var.environment}FranklinLoadBalancer"
  vpc_id = module.vpc.id

  tags = {
    Name        = "sg${var.environment}FranklinLoadBalancer",
    Project     = var.project
    Environment = var.environment
  }
}

resource "aws_security_group" "franklin" {
  name   = "sg${var.environment}FranklinEcsService"
  vpc_id = module.vpc.id

  tags = {
    Name        = "sg${var.environment}FranklinEcsService",
    Project     = var.project
    Environment = var.environment
  }
}

#
# ALB Resources
#
resource "aws_lb" "franklin" {
  name            = "alb${var.environment}Franklin"
  security_groups = [aws_security_group.alb.id]
  subnets         = module.vpc.public_subnet_ids

  enable_http2 = true

  tags = {
    Name        = "alb${var.environment}Franklin"
    Project     = var.project
    Environment = var.environment
  }
}

resource "aws_lb_target_group" "franklin" {
  name = "tg${var.environment}Franklin"

  health_check {
    healthy_threshold   = 3
    interval            = 30
    matcher             = 200
    protocol            = "HTTP"
    timeout             = 3
    path                = "/open-api/spec.yaml"
    unhealthy_threshold = 2
  }

  port     = 80
  protocol = "HTTP"
  vpc_id   = module.vpc.id

  target_type = "ip"

  tags = {
    Name        = "tg${var.environment}Franklin"
    Project     = var.project
    Environment = var.environment
  }
}

resource "aws_lb_listener" "franklin_redirect" {
  load_balancer_arn = aws_lb.franklin.arn
  port              = 80
  protocol          = "HTTP"

  default_action {
    type = "redirect"

    redirect {
      port        = 443
      protocol    = "HTTPS"
      status_code = "HTTP_301"
    }
  }
}

resource "aws_lb_listener" "franklin" {
  load_balancer_arn = aws_lb.franklin.id
  port              = 443
  protocol          = "HTTPS"
  certificate_arn   = module.cert.arn

  default_action {
    target_group_arn = aws_lb_target_group.franklin.id
    type             = "forward"
  }
}

#
# ECS Resources
#
resource "aws_ecs_cluster" "franklin" {
  name = "ecs${var.environment}Cluster"
}

resource "aws_ecs_task_definition" "franklin" {
  family                   = "${var.environment}Franklin"
  network_mode             = "awsvpc"
  requires_compatibilities = ["FARGATE"]
  cpu                      = var.franklin_cpu
  memory                   = var.franklin_memory

  task_role_arn      = aws_iam_role.ecs_task_role.arn
  execution_role_arn = aws_iam_role.ecs_task_execution_role.arn

  container_definitions = templatefile("${path.module}/task-definitions/franklin.json.tmpl", {
    image = "quay.io/azavea/franklin:${var.franklin_image_tag}"

    postgres_user     = var.rds_database_username
    postgres_password = var.rds_database_password
    postgres_host     = aws_route53_record.database.fqdn
    postgres_name     = "franklin"
    api_host          = aws_route53_record.franklin.name

    environment = var.environment
    aws_region  = var.aws_region
  })

  tags = {
    Name        = "${var.environment}Franklin",
    Project     = var.project
    Environment = var.environment
  }
}

resource "aws_ecs_task_definition" "franklin_migrations" {
  family                   = "${var.environment}FranklinMigrations"
  network_mode             = "awsvpc"
  requires_compatibilities = ["FARGATE"]
  cpu                      = var.franklin_migrations_cpu
  memory                   = var.franklin_migrations_memory

  task_role_arn      = aws_iam_role.ecs_task_role.arn
  execution_role_arn = aws_iam_role.ecs_task_execution_role.arn

  container_definitions = templatefile("${path.module}/task-definitions/franklin_migrations.json.tmpl", {
    image = "quay.io/azavea/franklin:${var.franklin_image_tag}"

    postgres_user     = var.rds_database_username
    postgres_password = var.rds_database_password
    postgres_host     = aws_route53_record.database.fqdn
    postgres_name     = "franklin"

    environment = var.environment
    aws_region  = var.aws_region
  })

  tags = {
    Name        = "${var.environment}FranklinMigrations",
    Project     = var.project
    Environment = var.environment
  }
}

resource "aws_ecs_service" "franklin" {
  name            = "${var.environment}Franklin"
  cluster         = aws_ecs_cluster.franklin.name
  task_definition = aws_ecs_task_definition.franklin.arn

  desired_count                      = var.franklin_desired_count
  deployment_minimum_healthy_percent = var.franklin_deployment_min_percent
  deployment_maximum_percent         = var.franklin_deployment_max_percent

  launch_type = "FARGATE"

  network_configuration {
    security_groups = [aws_security_group.franklin.id]
    subnets         = module.vpc.private_subnet_ids
  }


  load_balancer {
    target_group_arn = aws_lb_target_group.franklin.arn
    container_name   = "franklin"
    container_port   = 9090
  }

  depends_on = [aws_lb_listener.franklin]
}

#
# CloudWatch Resources
#
resource "aws_cloudwatch_log_group" "franklin" {
  name              = "log${var.environment}Franklin"
  retention_in_days = 30
}

resource "aws_cloudwatch_log_group" "franklin_migrations" {
  name              = "log${var.environment}FranklinMigrations"
  retention_in_days = 30
}

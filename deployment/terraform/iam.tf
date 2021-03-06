#
# Cross-account deployment role IAM resources
#
data "aws_iam_policy_document" "assume_deploy_role" {
  statement {
    effect = "Allow"

    principals {
      type = "AWS"
      identifiers = [var.aws_raster_foundry_account_id]
    }

    actions = ["sts:AssumeRole"]
  }
}

# This role requires a trust relationship to be established with the Raster
# Foundry AWS account. The Raster Foundry Jenkins instance profile needs to
# have the NOAA AWS account ID added to the list of principals in its
# attached AssumeRole policy. This will allow it to assume the cross-account
# deploy role.
resource "aws_iam_role" "deploy" {
  name               = "AzaveaDeploy"
  assume_role_policy = data.aws_iam_policy_document.assume_deploy_role.json
  description        = "Role assumed to execute CI based deployments for Azavea."
}

resource "aws_iam_role_policy_attachment" "deploy" {
  role       = aws_iam_role.deploy.name
  policy_arn = var.aws_administrator_policy_arn
}

#
# Container Instance IAM resources
#
data "aws_iam_policy_document" "container_instance_ec2_assume_role" {
  statement {
    effect = "Allow"

    principals {
      type        = "Service"
      identifiers = ["ec2.amazonaws.com"]
    }

    actions = ["sts:AssumeRole"]
  }
}

resource "aws_iam_role" "container_instance_ec2" {
  name               = "ContainerInstanceProfile"
  assume_role_policy = data.aws_iam_policy_document.container_instance_ec2_assume_role.json
}

resource "aws_iam_role_policy_attachment" "ec2_service_role" {
  role       = aws_iam_role.container_instance_ec2.name
  policy_arn = var.aws_ec2_service_role_policy_arn
}

resource "aws_iam_role_policy_attachment" "s3" {
  role       = aws_iam_role.container_instance_ec2.name
  policy_arn = var.aws_s3_full_access_policy_arn
}

resource "aws_iam_instance_profile" "container_instance" {
  name = aws_iam_role.container_instance_ec2.name
  role = aws_iam_role.container_instance_ec2.name
}

#
# Spot Fleet IAM resources
#
data "aws_iam_policy_document" "container_instance_spot_fleet_assume_role" {
  statement {
    effect = "Allow"

    principals {
      type        = "Service"
      identifiers = ["spotfleet.amazonaws.com"]
    }

    actions = ["sts:AssumeRole"]
  }
}

resource "aws_iam_role" "container_instance_spot_fleet" {
  name               = "fleetServiceRole"
  assume_role_policy = data.aws_iam_policy_document.container_instance_spot_fleet_assume_role.json
}

resource "aws_iam_role_policy_attachment" "spot_fleet_policy" {
  role       = aws_iam_role.container_instance_spot_fleet.name
  policy_arn = var.aws_spot_fleet_service_role_policy_arn
}

#
# Batch IAM resources
#
data "aws_iam_policy_document" "container_instance_batch_assume_role" {
  statement {
    effect = "Allow"

    principals {
      type        = "Service"
      identifiers = ["batch.amazonaws.com"]
    }

    actions = ["sts:AssumeRole"]
  }
}

resource "aws_iam_role" "container_instance_batch" {
  name               = "batchServiceRole"
  assume_role_policy = data.aws_iam_policy_document.container_instance_batch_assume_role.json
}

resource "aws_iam_role_policy_attachment" "batch_policy" {
  role       = aws_iam_role.container_instance_batch.name
  policy_arn = var.aws_batch_service_role_policy_arn
}

#
# ECS IAM resources
#
data "aws_iam_policy_document" "ecs_assume_role" {
  statement {
    effect = "Allow"

    principals {
      type        = "Service"
      identifiers = ["ecs-tasks.amazonaws.com"]
    }

    actions = [
      "sts:AssumeRole",
    ]
  }
}

resource "aws_iam_role" "ecs_task_execution_role" {
  name               = "ecsTaskExecutionRole"
  assume_role_policy = data.aws_iam_policy_document.ecs_assume_role.json
}

resource "aws_iam_role" "ecs_task_role" {
  name               = "ecsTaskRole"
  assume_role_policy = data.aws_iam_policy_document.ecs_assume_role.json
}

resource "aws_iam_role_policy_attachment" "ecs_task_execution_role_policy" {
  role       = aws_iam_role.ecs_task_execution_role.name
  policy_arn = var.aws_ecs_task_execution_role_policy_arn
}

#
# Security Group resources
#
resource "aws_security_group" "batch" {
  vpc_id = module.vpc.id

  tags = {
    Name    = "sgBatchContainerInstance"
    Project = var.project
  }
}

#
# Batch resources
#
# Pull the image IDs for the latest Amazon ECS optimized AMIs
# https://docs.aws.amazon.com/AmazonECS/latest/developerguide/ecs-optimized_AMI.html
data "aws_ssm_parameter" batch_cpu_container_instance_image_id {
  name = "/aws/service/ecs/optimized-ami/amazon-linux-2/recommended/image_id"
}

data "aws_ssm_parameter" batch_gpu_container_instance_image_id {
  name = "/aws/service/ecs/optimized-ami/amazon-linux-2/gpu/recommended/image_id"
}

resource "aws_launch_template" "batch_cpu_container_instance" {
  name_prefix = "ltBatchCPUContainerInstance-"

  block_device_mappings {
    device_name = "/dev/xvda"

    ebs {
      volume_size = var.batch_cpu_container_instance_volume_size
      volume_type = "gp2"
    }
  }

  user_data = filebase64("cloud-config/batch-container-instance.yml.tmpl")
}

resource "aws_launch_template" "batch_gpu_container_instance" {
  name_prefix = "ltBatchGPUContainerInstance-"

  block_device_mappings {
    device_name = "/dev/xvda"

    ebs {
      volume_size = var.batch_gpu_container_instance_volume_size
      volume_type = "gp2"
    }
  }
}

resource "aws_batch_compute_environment" "cpu" {
  depends_on = [aws_iam_role_policy_attachment.batch_policy]

  compute_environment_name_prefix = "batchCPUComputeEnvironment"
  type                            = "MANAGED"
  state                           = "ENABLED"
  service_role                    = aws_iam_role.container_instance_batch.arn

  compute_resources {
    type                = "SPOT"
    allocation_strategy = var.batch_cpu_ce_spot_fleet_allocation_strategy
    bid_percentage      = var.batch_cpu_ce_spot_fleet_bid_precentage
    ec2_key_pair        = var.aws_key_name
    image_id            = data.aws_ssm_parameter.batch_cpu_container_instance_image_id.value

    min_vcpus = var.batch_cpu_ce_min_vcpus
    max_vcpus = var.batch_cpu_ce_max_vcpus

    spot_iam_fleet_role = aws_iam_role.container_instance_spot_fleet.arn
    instance_role       = aws_iam_instance_profile.container_instance.arn

    instance_type = var.batch_cpu_ce_instance_types

    launch_template {
      launch_template_id = aws_launch_template.batch_cpu_container_instance.id
      version            = aws_launch_template.batch_cpu_container_instance.latest_version
    }

    security_group_ids = [
      aws_security_group.batch.id
    ]

    subnets = module.vpc.private_subnet_ids

    tags = {
      Name               = "BatchWorker"
      ComputeEnvironment = "CPU"
      Project            = var.project
    }
  }

  lifecycle {
    create_before_destroy = true
  }
}

resource "aws_batch_compute_environment" "gpu" {
  depends_on = [aws_iam_role_policy_attachment.batch_policy]

  compute_environment_name_prefix = "batchGPUComputeEnvironment"
  type                            = "MANAGED"
  state                           = "ENABLED"
  service_role                    = aws_iam_role.container_instance_batch.arn

  compute_resources {
    type                = "SPOT"
    allocation_strategy = var.batch_gpu_ce_spot_fleet_allocation_strategy
    bid_percentage      = var.batch_gpu_ce_spot_fleet_bid_precentage
    ec2_key_pair        = var.aws_key_name
    image_id            = data.aws_ssm_parameter.batch_gpu_container_instance_image_id.value

    min_vcpus = var.batch_gpu_ce_min_vcpus
    max_vcpus = var.batch_gpu_ce_max_vcpus

    spot_iam_fleet_role = aws_iam_role.container_instance_spot_fleet.arn
    instance_role       = aws_iam_instance_profile.container_instance.arn

    instance_type = var.batch_gpu_ce_instance_types

    launch_template {
      launch_template_id = aws_launch_template.batch_gpu_container_instance.id
      version            = aws_launch_template.batch_gpu_container_instance.latest_version
    }

    security_group_ids = [
      aws_security_group.batch.id
    ]

    subnets = module.vpc.private_subnet_ids

    tags = {
      Name               = "BatchWorker"
      ComputeEnvironment = "GPU"
      Project            = var.project
    }
  }

  lifecycle {
    create_before_destroy = true
  }
}

resource "aws_batch_job_queue" "cpu" {
  name                 = "queueCPU"
  priority             = 1
  state                = "ENABLED"
  compute_environments = [aws_batch_compute_environment.cpu.arn]
}

resource "aws_batch_job_queue" "gpu" {
  name                 = "queueGPU"
  priority             = 1
  state                = "ENABLED"
  compute_environments = [aws_batch_compute_environment.gpu.arn]
}

resource "aws_batch_job_definition" "test_cpu" {
  name = "jobTestCPU"
  type = "container"

  container_properties = templatefile("job-definitions/test-cpu.json.tmpl", {})
}

resource "aws_batch_job_definition" "test_gpu" {
  name = "jobTestGPU"
  type = "container"

  container_properties = templatefile("job-definitions/test-gpu.json.tmpl", {})
}

resource "aws_batch_job_definition" "s2_catalog_creation" {
  name = "createSentinel2Catalogs"
  type = "container"

  container_properties = templatefile("job-definitions/sentinel-2-catalog-creation.json.tmpl", {})
}

resource "aws_batch_job_definition" "franklin_import_items" {
  name = "importItemsFranklin"
  type = "container"

  container_properties = templatefile("job-definitions/franklin-import.json.tmpl", {
    postgres_user     = var.rds_database_username
    postgres_password = var.rds_database_password
    postgres_host     = aws_route53_record.database.fqdn
    postgres_name     = "franklin"
    api_host          = aws_route53_record.franklin.name
  })
}


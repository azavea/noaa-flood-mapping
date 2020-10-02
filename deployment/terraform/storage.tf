module "ecr_catalogs" {
  source = "github.com/azavea/terraform-aws-ecr-repository?ref=1.0.0"

  repository_name         = "noaa-flood-catalogs"
  attach_lifecycle_policy = true
}

module "ecr_pipeline" {
  source = "github.com/azavea/terraform-aws-ecr-repository?ref=1.0.0"

  repository_name         = "noaa-flood-pipeline"
  attach_lifecycle_policy = true
}

resource "aws_s3_bucket" "data" {
  bucket = "noaafloodmap-data-${var.aws_region}"
  acl    = "private"

  tags = {
    Name    = "noaafloodmap-data-${var.aws_region}"
    Project = var.project
  }
}

resource "aws_s3_bucket" "data" {
  bucket = "noaafloodmap-${lower(var.environment)}-data-${var.aws_region}"
  acl    = "private"

  tags = {
    Name        = "noaafloodmap-${lower(var.environment)}-data-${var.aws_region}"
    Project     = var.project
    Environment = var.environment
  }
}

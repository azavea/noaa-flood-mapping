resource "aws_s3_bucket" "data" {
  bucket = "noaafloodmap-data-${var.aws_region}"
  acl    = "private"

  tags = {
    Name    = "noaafloodmap-data-${var.aws_region}"
    Project = var.project
  }
}

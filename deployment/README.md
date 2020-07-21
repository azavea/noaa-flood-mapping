# Deployment

- [AWS Credentials](#aws-credentials)
- [Publish Container Images](#publish-container-images)
- [Terraform](#terraform)

## AWS Credentials

Using the AWS CLI, create an AWS profile named `noaa`:

```bash
$ aws configure --profile noaa
AWS Access Key ID [None]: AKIAIOSFODNN7EXAMPLE
AWS Secret Access Key [None]: wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY
Default region name [None]: us-east-1
Default output format [None]:
```

You will be prompted to enter your AWS credentials, along with a default region. These credentials will be used to authenticate calls to the AWS API when using Terraform and the AWS CLI.

## Terraform

First, we need to make sure there is a `terraform.tfvars` file in the project settings bucket on S3. The `.tfvars` file is where we can change specific attributes of the project's infrastructure, not defined in the `variables.tf` file.

Here is an example `terraform.tfvars` for this project:

```hcl
project     = "Flood Mapping"
environment = "Staging"
aws_region  = "us-east-1"

aws_key_name = "floodmapping-stg"

r53_private_hosted_zone = "floodmapping.noaa.internal"

external_access_cidr_block = "127.0.0.1/32"

bastion_ami           = "ami-0a887e401f7654935"
bastion_instance_type = "t3.nano"
bastion_ebs_optimized = true

rds_database_identifier = floodmapping-staging
rds_database_name       = floodmapping
rds_database_username   = floodmapping
rds_database_password   = floodmapping
```

This file lives at `s3://floodmapping-staging-config-us-east-1/terraform/terraform.tfvars`.

To deploy this project's core infrastructure, use the `infra` wrapper script to lookup the remote state of the infrastructure and assemble a plan for work to be done:

```bash
$ docker-compose -f docker-compose.ci.yml run --rm terraform
$ ./scripts/infra plan
```

Once the plan has been assembled, and you agree with the changes, apply it:

```bash
$ ./scripts/infra apply
```

This will attempt to apply the plan assembled in the previous step using Amazon's APIs.

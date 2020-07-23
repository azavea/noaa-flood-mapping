# Deployment

- [AWS Credentials](#aws-credentials)
- [Terraform](#terraform)
- [Bastion](#bastion)
  - [PostgreSQL Client](#postgresql-client)

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
project     = "Flood Map"
environment = "Staging"
aws_region  = "us-east-1"

aws_key_name = "floodmap-stg"

r53_private_hosted_zone = "floodmap.noaa.internal"

external_access_cidr_block = "127.0.0.1/32"

bastion_ami           = "ami-08f3d892de259504d"
bastion_instance_type = "t3.nano"
bastion_ebs_optimized = true

rds_database_identifier = floodmap-staging
rds_database_name       = floodmap
rds_database_username   = floodmap
rds_database_password   = floodmap
```

This file lives at `s3://noaafloodmap-staging-config-us-east-1/terraform/terraform.tfvars`.

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

## Bastion

### PostgreSQL Client

The bastion SSH host created by Terraform has several utility libraries installed on it, including a PostgreSQL 12 client. At the time that this client was installed, PostgreSQL 12 support was new to RDS and the client for 12 was not available on the `amazon-linux-extras` repository.

To perform an upgrade, the existing `postgresql12`, `libpq5`, and `postgresql12-libs` packages should be uninstalled and the newer versions should be installed from [this repository](https://download.postgresql.org/pub/repos/yum/12/redhat/rhel-7-x86_64/).

When `amazon-linux-extras` adds PostgreSQL 12 libraries, the manually installed RPMs can be replaced with the packages in `amazon-linux-extras`.

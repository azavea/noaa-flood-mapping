#
# Bastion security group resources
#
resource "aws_security_group_rule" "bastion_ssh_ingress" {
  type        = "ingress"
  from_port   = 22
  to_port     = 22
  protocol    = "tcp"
  cidr_blocks = [var.external_access_cidr_block]

  security_group_id = module.vpc.bastion_security_group_id
}

resource "aws_security_group_rule" "bastion_ssh_egress" {
  type      = "egress"
  from_port = 22
  to_port   = 22
  protocol  = "tcp"

  security_group_id        = module.vpc.bastion_security_group_id
  source_security_group_id = aws_security_group.batch.id
}

resource "aws_security_group_rule" "bastion_rds_egress" {
  type      = "egress"
  from_port = module.database.port
  to_port   = module.database.port
  protocol  = "tcp"

  security_group_id        = module.vpc.bastion_security_group_id
  source_security_group_id = module.database.database_security_group_id
}

#
# RDS security group resources
#
resource "aws_security_group_rule" "rds_bastion_ingress" {
  type      = "ingress"
  from_port = module.database.port
  to_port   = module.database.port
  protocol  = "tcp"

  security_group_id        = module.database.database_security_group_id
  source_security_group_id = module.vpc.bastion_security_group_id
}

resource "aws_security_group_rule" "rds_container_instance_ingress" {
  type      = "ingress"
  from_port = module.database.port
  to_port   = module.database.port
  protocol  = "tcp"

  security_group_id        = module.database.database_security_group_id
  source_security_group_id = aws_security_group.batch.id
}

#
# Container instance security group resources
#
resource "aws_security_group_rule" "container_instance_ssh_ingress" {
  type      = "ingress"
  from_port = 22
  to_port   = 22
  protocol  = "tcp"

  security_group_id        = aws_security_group.batch.id
  source_security_group_id = module.vpc.bastion_security_group_id
}

resource "aws_security_group_rule" "container_instance_https_egress" {
  type        = "egress"
  from_port   = 443
  to_port     = 443
  protocol    = "tcp"
  cidr_blocks = ["0.0.0.0/0"]

  security_group_id = aws_security_group.batch.id
}

resource "aws_security_group_rule" "container_instance_rds_egress" {
  type      = "egress"
  from_port = module.database.port
  to_port   = module.database.port
  protocol  = "tcp"

  security_group_id        = aws_security_group.batch.id
  source_security_group_id = module.database.database_security_group_id
}

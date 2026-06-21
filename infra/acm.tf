resource "aws_acm_certificate" "frontend" {
  provider                  = aws.use1
  domain_name               = var.app_domain_name
  subject_alternative_names = [var.admin_domain_name]
  validation_method         = "DNS"

  tags = local.tags

  lifecycle {
    create_before_destroy = true
    prevent_destroy       = true
  }
}

data "aws_route53_zone" "primary" {
  name         = var.route53_zone_name
  private_zone = false
}

locals {
  frontend_certificate_validation_options = {
    for option in aws_acm_certificate.frontend.domain_validation_options : option.domain_name => {
      name  = option.resource_record_name
      type  = option.resource_record_type
      value = option.resource_record_value
    }
  }
}

resource "aws_route53_record" "frontend_certificate_validation" {
  for_each = local.frontend_certificate_validation_options

  zone_id         = data.aws_route53_zone.primary.zone_id
  name            = each.value.name
  type            = each.value.type
  ttl             = 60
  records         = [each.value.value]
  allow_overwrite = true
}

resource "aws_acm_certificate_validation" "frontend" {
  provider = aws.use1

  certificate_arn         = aws_acm_certificate.frontend.arn
  validation_record_fqdns = [for record in aws_route53_record.frontend_certificate_validation : record.fqdn]
}

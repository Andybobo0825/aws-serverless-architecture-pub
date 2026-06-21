output "cognito_user_pool_id" {
  value = aws_cognito_user_pool.main.id
}

output "cognito_user_pool_client_id" {
  value = aws_cognito_user_pool_client.app.id
}

output "api_gateway_url" {
  value = aws_apigatewayv2_api.api.api_endpoint
}

output "app_frontend_bucket" {
  value = aws_s3_bucket.app_frontend.bucket
}

output "admin_frontend_bucket" {
  value = aws_s3_bucket.admin_frontend.bucket
}

output "content_bucket" {
  value = aws_s3_bucket.content.bucket
}

output "app_cloudfront_domain_name" {
  value = aws_cloudfront_distribution.app.domain_name
}

output "admin_cloudfront_domain_name" {
  value = aws_cloudfront_distribution.admin.domain_name
}

output "acm_dns_validation_records" {
  value = {
    for option in aws_acm_certificate.frontend.domain_validation_options : option.domain_name => {
      name  = option.resource_record_name
      type  = option.resource_record_type
      value = option.resource_record_value
    }
  }
}


output "app_cloudfront_distribution_id" {
  value = aws_cloudfront_distribution.app.id
}

output "admin_cloudfront_distribution_id" {
  value = aws_cloudfront_distribution.admin.id
}

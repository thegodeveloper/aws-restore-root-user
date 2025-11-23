output "secret_arns" {
  description = "ARNs of secrets containing root user credentials"
  value = {
    for name, secret in aws_secretsmanager_secret.root_credentials :
    name => secret.arn
  }
}

output "account_details" {
  description = "Account details for password setup"
  value = {
    for name, account in var.accounts : name => {
      account_id = account.account_id
      email      = account.email
      login_url  = "https://${account.account_id}.signin.aws.amazon.com/console"
      secret_arn = aws_secretsmanager_secret.root_credentials[name].arn
    }
  }
}

output "setup_instructions" {
  description = "Instructions for setting up root user passwords"
  value       = <<-EOT

    ═══════════════════════════════════════════════════════════════════════════════
    ROOT USER PASSWORD SETUP INSTRUCTIONS
    ═══════════════════════════════════════════════════════════════════════════════

    Your AWS accounts have been created and passwords have been generated and
    stored securely in AWS Secrets Manager.

    PASSWORD RESET:
    ──────────────────────
    For each account:

    1. Get credentials from Secrets Manager:
       aws secretsmanager get-secret-value \
         --secret-id ${var.secrets_prefix}/ACCOUNT_NAME \
         --query SecretString --output text | jq -r '.password'

    2. Go to: https://ACCOUNT_ID.signin.aws.amazon.com/console
    3. Click "Forgot password?"
    4. Check the email: ACCOUNT_EMAIL
    5. Follow the reset link and use the password from step 1

    ACCOUNT LOGIN URLS:
    ───────────────────
    After password reset, use these direct login URLs:

    ${join("\n    ", [for name, account in var.accounts : "• ${name}: https://${account.account_id}.signin.aws.amazon.com/console"])}

    SECURITY NOTES:
    ───────────────
    • Passwords are stored encrypted in AWS Secrets Manager
    • Restrict access to secrets using IAM policies
    • Enable MFA on all root accounts after initial setup
    • Consider rotating passwords regularly
    • Use the automation script to maintain security best practices

    ═══════════════════════════════════════════════════════════════════════════════
  EOT
}

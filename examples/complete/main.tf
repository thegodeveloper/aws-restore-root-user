# Example: Automated password reset for your existing AWS accounts
#
# This example shows how to use the module to actually set passwords
# using browser automation and email integration.

# Create a TEST Organization Unit
resource "aws_organizations_organizational_unit" "test" {
  name      = "TEST"
  parent_id = var.parent_ou_id
}

# Your existing account creation code
resource "aws_organizations_account" "production_accounts" {
  count = 0
  name      = "prod-account-${count.index + 1}"
  email     = "prod-account-${count.index + 1}+${var.email_username}@gmail.com"
  parent_id = aws_organizations_organizational_unit.test.id
}

resource "aws_organizations_account" "development_accounts" {
  count = 1
  name      = "dev-account-${count.index + 1}"
  email     = "dev-account-${count.index + 1}+${var.email_username}@gmail.com"
  parent_id = aws_organizations_organizational_unit.test.id
}

# Reference existing email password secret in Secrets Manager
data "aws_secretsmanager_secret" "email_password" {
  name = "email-app-password"
}

# Use the module WITH AUTOMATION to actually set passwords
module "root_passwords" {
  source = "../../modules/root-user-access"

  accounts = merge(
    {
      for idx, account in aws_organizations_account.production_accounts :
      "prod-account-${idx + 1}" => {
        account_id = account.id
        email      = account.email
        ou         = "Production"
      }
    },
    {
      for idx, account in aws_organizations_account.development_accounts :
      "dev-account-${idx + 1}" => {
        account_id = account.id
        email      = account.email
        ou         = "Development"
      }
    }
  )

  # Enable automated password reset
  auto_reset_passwords = true

  # Email configuration (required for automation)
  email_imap_server       = "imap.gmail.com"
  email_imap_port         = 993
  email_address           = var.email_address
  email_password_secret   = data.aws_secretsmanager_secret.email_password.id

  # Automation settings
  headless_browser        = true   # Run browser in background
  wait_for_email_seconds  = 120    # Wait up to 2 minutes for reset email
  automation_timeout      = 300    # 5 minute timeout per account

  # Optional: Force reset on every apply
  # force_password_reset = true
}





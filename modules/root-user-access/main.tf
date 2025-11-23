# Generate secure random passwords for each account
resource "random_password" "root_passwords" {
  for_each = var.accounts

  length           = var.password_length
  special          = true
  min_upper        = 2
  min_lower        = 2
  min_numeric      = 2
  min_special      = 2
  override_special = "!@#$%^&*()-_=+[]{}|;:,.<>?"
}

# Store credentials in AWS Secrets Manager
resource "aws_secretsmanager_secret" "root_credentials" {
  for_each = var.accounts

  name                    = "${var.secrets_prefix}/${each.key}"
  description             = "Root user credentials for AWS account ${each.key} (${each.value.account_id})"
  recovery_window_in_days = var.secret_recovery_days

  tags = merge(
    var.tags,
    {
      ManagedBy   = "Terraform"
      AccountName = each.key
      AccountID   = each.value.account_id
      Purpose     = "RootUserAccess"
    }
  )
}

resource "aws_secretsmanager_secret_version" "root_credentials" {
  for_each = var.accounts

  secret_id = aws_secretsmanager_secret.root_credentials[each.key].id
  secret_string = jsonencode({
    account_id   = each.value.account_id
    account_name = each.key
    email        = each.value.email
    password     = random_password.root_passwords[each.key].result
    login_url    = "https://${each.value.account_id}.signin.aws.amazon.com/console"
    password_set = false  # Will be updated to true after automation completes
    metadata = {
      ou         = lookup(each.value, "ou", "")
      created_at = timestamp()
    }
  })

  lifecycle {
    ignore_changes = [secret_string]
  }
}

# Create configuration file for password reset automation
resource "local_file" "automation_config" {
  filename = "${path.module}/../../.password-reset-config.json"
  content = jsonencode({
    accounts = {
      for name, account in var.accounts : name => {
        account_id = account.account_id
        email      = account.email
        secret_id  = aws_secretsmanager_secret.root_credentials[name].id
        login_url  = "https://${account.account_id}.signin.aws.amazon.com/console"
      }
    }
    email_config = {
      imap_server   = var.email_imap_server
      imap_port     = var.email_imap_port
      email_address = var.email_address
      email_password_secret = var.email_password_secret
    }
    automation = {
      headless        = var.headless_browser
      timeout_seconds = var.automation_timeout
      wait_for_email  = var.wait_for_email_seconds
    }
  })

  depends_on = [
    aws_secretsmanager_secret_version.root_credentials
  ]
}

# Trigger password reset automation
resource "null_resource" "password_reset_automation" {
  for_each = var.auto_reset_passwords ? var.accounts : {}

  triggers = {
    account_id = each.value.account_id
    email      = each.value.email
    secret_id  = aws_secretsmanager_secret.root_credentials[each.key].id
    always_run = var.force_password_reset ? timestamp() : null
  }

  provisioner "local-exec" {
    command = <<-EOT
      bash ${path.module}/../../scripts/run-password-reset.sh \
        --account-name "${each.key}" \
        --account-id "${each.value.account_id}" \
        --email "${each.value.email}" \
        --secret-id "${aws_secretsmanager_secret.root_credentials[each.key].id}" \
        --config "${path.module}/../../.password-reset-config.json" \
        ${var.headless_browser ? "--headless" : ""} \
        ${var.skip_mfa_setup ? "--skip-mfa" : ""}
    EOT

    environment = {
      AWS_REGION = data.aws_region.current.name
    }
  }

  depends_on = [
    local_file.automation_config,
    aws_secretsmanager_secret_version.root_credentials
  ]
}

data "aws_region" "current" {}

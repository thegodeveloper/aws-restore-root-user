variable "accounts" {
  description = <<-EOT
    Map of account names to account details for password management.

    Required fields:
      - account_id: AWS account ID (12 digits)
      - email: Root user email address

    Optional fields:
      - ou: Organizational Unit name
      - tags: Additional tags
  EOT

  type = map(object({
    account_id = string
    email      = string
    ou         = optional(string, "")
    tags       = optional(map(string), {})
  }))

  validation {
    condition = alltrue([
      for account in var.accounts :
      can(regex("^[0-9]{12}$", account.account_id))
    ])
    error_message = "All account_id values must be 12-digit numbers."
  }

  validation {
    condition = alltrue([
      for account in var.accounts :
      can(regex("^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\\.[a-zA-Z]{2,}$", account.email))
    ])
    error_message = "All email values must be valid email addresses."
  }
}

variable "password_length" {
  description = "Length of generated root passwords (14-128 characters)"
  type        = number
  default     = 32

  validation {
    condition     = var.password_length >= 14 && var.password_length <= 128
    error_message = "Password length must be between 14 and 128 characters."
  }
}

variable "secrets_prefix" {
  description = "Prefix for Secrets Manager secret names"
  type        = string
  default     = "root-user"
}

variable "secret_recovery_days" {
  description = "Number of days to retain deleted secrets (0 or 7-30)"
  type        = number
  default     = 30

  validation {
    condition     = var.secret_recovery_days == 0 || (var.secret_recovery_days >= 7 && var.secret_recovery_days <= 30)
    error_message = "Recovery days must be 0 or between 7 and 30."
  }
}

variable "tags" {
  description = "Additional tags for Secrets Manager secrets"
  type        = map(string)
  default     = {}
}

# Email Configuration for Password Reset Automation
variable "email_imap_server" {
  description = "IMAP server for retrieving password reset emails (e.g., imap.gmail.com)"
  type        = string
  default     = ""
}

variable "email_imap_port" {
  description = "IMAP server port (usually 993 for SSL)"
  type        = number
  default     = 993
}

variable "email_address" {
  description = "Email address to check for password reset emails"
  type        = string
  default     = ""
}

variable "email_password_secret" {
  description = "AWS Secrets Manager secret ID containing email password/app password"
  type        = string
  default     = ""
}

# Automation Configuration
variable "auto_reset_passwords" {
  description = "Automatically reset passwords using browser automation (requires email configuration)"
  type        = bool
  default     = false
}

variable "force_password_reset" {
  description = "Force password reset even if already set (runs on every apply)"
  type        = bool
  default     = false
}

variable "headless_browser" {
  description = "Run browser automation in headless mode"
  type        = bool
  default     = true
}

variable "automation_timeout" {
  description = "Timeout in seconds for password reset automation"
  type        = number
  default     = 300
}

variable "wait_for_email_seconds" {
  description = "How long to wait for password reset email to arrive"
  type        = number
  default     = 60
}

variable "skip_mfa_setup" {
  description = "Skip MFA setup during automated password reset"
  type        = bool
  default     = true
}

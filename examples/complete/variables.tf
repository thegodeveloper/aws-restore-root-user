# Required
variable "parent_ou_id" {
  description = "Parent organizational unit ID (typically your root organization ID)"
  type        = string
}

variable "email_address" {
  description = "Email Address"
  type        = string
  sensitive   = true
}

variable "email_username" {
  description = "Email Username"
  type        = string
  sensitive   = true
}

variable "email_app_password" {
  description = "Email app password for IMAP access (Gmail app password recommended)"
  type        = string
  sensitive   = true
}

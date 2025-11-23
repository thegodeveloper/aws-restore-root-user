# Outputs
output "password_reset_status" {
  description = "Status of password reset automation"
  value       = module.root_passwords.account_details
  sensitive   = true
}

output "accounts_with_passwords_set" {
  description = "Accounts where passwords were successfully set"
  value = {
    for name, details in module.root_passwords.account_details :
    name => details if lookup(details, "password_set", false)
  }
  sensitive = true
}
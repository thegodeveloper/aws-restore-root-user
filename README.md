# AWS Root User Password Reset Automation Module

** This module is not working yet **

A Terraform module that **actually sets/assigns/recovers passwords** for AWS root users using browser automation and email integration.

## What This Module Does

This module **actually sets the password** on your AWS accounts by:

1. **Generating** secure random passwords
2. **Storing** them in AWS Secrets Manager
3. **Automatically navigating** to AWS login page
4. **Triggering** the "Forgot Password" flow
5. **Retrieving** the password reset email from your inbox
6. **Clicking** the reset link automatically
7. **Setting** the new password via browser automation
8. **Verifying** the login works

## How It Works

```
Terraform Apply
    ↓
Generate Random Password → Store in Secrets Manager
    ↓
Trigger Browser Automation (Selenium)
    ↓
Navigate to AWS Login → Click "Forgot Password"
    ↓
AWS Sends Reset Email
    ↓
Script Retrieves Email (IMAP) → Extracts Reset Link
    ↓
Open Reset Link → Enter New Password
    ↓
Submit Form → Verify Login
    ↓
✓ Password Successfully Set!
```

## Requirements

### System Dependencies
```bash
# Create a virtual environment
python3 -m venv venv

# Activate the virtual environment
source venv/bin/activate

# Install Python dependencies
pip install -r requirements.txt

# Chrome/Chromium (for Selenium)
# Linux:
sudo apt-get install chromium chromium-driver

# macOS:
brew install --cask google-chrome
```

### AWS Permissions
- `secretsmanager:GetSecretValue`
- `secretsmanager:PutSecretValue`
- `secretsmanager:CreateSecret`

### Email Configuration

You need IMAP access to the email account that receives AWS password reset emails.

**For Gmail:**
1. Enable 2FA on your Google account
2. Generate an App Password: https://myaccount.google.com/apppasswords
3. Store it in AWS Secrets Manager

```bash
aws secretsmanager create-secret \
  --name email-app-password \
  --secret-string "your-app-password-here"
```

**For other providers:**
- Use your IMAP server settings
- May need an app-specific password

## Usage

### Option 1: Fully Automated (Recommended)

Set passwords automatically during `terraform apply`:

```hcl
# Your existing account creation
resource "aws_organizations_account" "accounts" {
  count = 2
  name  = "account-${count.index + 1}"
  email = "account-${count.index + 1}@example.com"
  # ...
}

# Store email password in Secrets Manager
resource "aws_secretsmanager_secret" "email_password" {
  name = "email-app-password"
}

resource "aws_secretsmanager_secret_version" "email_password" {
  secret_id     = aws_secretsmanager_secret.email_password.id
  secret_string = var.email_app_password
}

# Use the module with automation ENABLED
module "root_passwords" {
  source = "./modules/root-user-access"

  accounts = {
    for idx, account in aws_organizations_account.accounts :
    account.name => {
      account_id = account.id
      email      = account.email
    }
  }

  # ENABLE AUTOMATION - This actually sets the passwords!
  auto_reset_passwords = true

  # Email configuration (required for automation)
  email_imap_server     = "imap.gmail.com"
  email_imap_port       = 993
  email_address         = "your-email@example.com"
  email_password_secret = aws_secretsmanager_secret.email_password.id

  # Automation settings
  headless_browser       = true   # Run browser in background
  wait_for_email_seconds = 120    # Wait up to 2 min for email
}
```

Then run:
```bash
terraform init
terraform apply
```

The module will:
- Generate passwords for all 12 accounts
- Automatically reset each password
- Set the generated password
- Verify login works

## Module Variables

| Variable | Description | Default | Required |
|----------|-------------|---------|----------|
| `accounts` | Map of account details (account_id, email) | - | ✓ |
| `auto_reset_passwords` | **Enable automation to actually set passwords** | `false` | |
| `email_imap_server` | IMAP server (e.g., imap.gmail.com) | `""` | If auto_reset |
| `email_imap_port` | IMAP port | `993` | |
| `email_address` | Email to check for reset links | `""` | If auto_reset |
| `email_password_secret` | Secret ID with email password | `""` | If auto_reset |
| `headless_browser` | Run browser in background | `true` | |
| `wait_for_email_seconds` | Wait time for reset email | `60` | |
| `password_length` | Password length | `32` | |
| `secrets_prefix` | Prefix for secret names | `"root-user"` | |

## Module Outputs

| Output | Description |
|--------|-------------|
| `secret_arns` | Secret ARNs with passwords |
| `account_details` | Account details including password_set status |
| `account_login_urls` | Direct login URLs |
| `setup_instructions` | Instructions if automation is disabled |

## Email Provider Setup

### Gmail
```hcl
email_imap_server = "imap.gmail.com"
email_imap_port   = 993
email_address     = "you@gmail.com"
```

Create app password: https://myaccount.google.com/apppasswords

### Outlook/Office 365
```hcl
email_imap_server = "outlook.office365.com"
email_imap_port   = 993
email_address     = "you@outlook.com"
```

### Custom IMAP Server
```hcl
email_imap_server = "imap.yourdomain.com"
email_imap_port   = 993
email_address     = "aws-accounts@yourdomain.com"
```

## Verification

Check if passwords were set:

```bash
# View automation results
terraform output -json module.root_passwords.account_details | jq .

# Check specific account
aws secretsmanager get-secret-value \
  --secret-id root-user/account-name \
  --query SecretString | jq .

# Test login manually
# URL from: terraform output account_login_urls
# Password from: aws secretsmanager get-secret-value --secret-id root-user/account-name
```

## Troubleshooting

### "Email configuration not provided"
Set the email variables or run without automation:
```hcl
auto_reset_passwords = false
```

### "Failed to retrieve password reset email"
- Check email credentials are correct
- Verify IMAP is enabled on your email account
- Check spam folder
- Increase `wait_for_email_seconds`

### "Browser initialization failed"
Install Chrome/Chromium:
```bash
# Linux
sudo apt-get install chromium-browser

# macOS
brew install --cask google-chrome
```

### "Selenium errors"
```bash
pip install --upgrade selenium webdriver-manager
```

### See automation in action
Run without headless mode:
```hcl
headless_browser = false
```

## Security Considerations

1. **Email Security**: Use app-specific passwords, not your main password
2. **Secrets Access**: Restrict who can read secrets
3. **Terraform State**: Contains passwords - use encrypted remote backend
4. **MFA**: Enable MFA on all root accounts after password is set
5. **Root Usage**: Only use root when absolutely necessary

## Advanced Configuration

### Force Reset on Every Apply
```hcl
force_password_reset = true
```

### Custom Timeout
```hcl
automation_timeout      = 600  # 10 minutes
wait_for_email_seconds  = 180  # 3 minutes
```

### Password Complexity
```hcl
password_length = 64  # Longer passwords
```

## Scripts Provided

| Script | Purpose |
|--------|---------|
| `run-password-reset.sh` | Main wrapper called by Terraform |
| `setup-python-env.sh` | Sets up Python venv and installs dependencies |
| `automated-password-reset.py` | Core password reset automation |

## Examples

See example files:
- `example-with-automation.tf` - Full automation setup
- `example-manual-trigger.tf` - Manual trigger setup

## Cost

- **Secrets Manager**: $0.40/secret/month
- **12 accounts**: ~$5.20/month
- **Automation**: Free (local execution)

## What Makes This Different

**Other solutions:**
- ✗ Only generate passwords
- ✗ Only store in Secrets Manager
- ✗ Require manual password reset

**This module:**
- ✓ Generates AND sets passwords
- ✓ Fully automated browser interaction
- ✓ Retrieves reset emails automatically
- ✓ Completes entire password reset flow
- ✓ Verifies login success
- ✓ Updates password status

## Important Notes

1. **AWS Limitation**: AWS has no API to set root passwords directly. This module works around it using browser automation.

2. **Email Required**: For full automation, you must provide email IMAP access.

3. **One-time Setup**: After passwords are set, you can disable automation:
   ```hcl
   auto_reset_passwords = false
   ```

4. **Enable MFA**: Immediately enable MFA on all root accounts after setup.

## Support

- Browser automation: Selenium WebDriver
- Email retrieval: Python imaplib
- AWS integration: Boto3

## License

Provided as-is for AWS Account Management Automation by WMR.

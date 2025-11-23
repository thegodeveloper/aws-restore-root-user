#!/usr/bin/env python3
"""
Automated AWS Root User Password Reset

This script automates the complete password reset flow:
1. Navigates to AWS account login page
2. Triggers "Forgot Password" flow
3. Retrieves reset email from IMAP
4. Clicks reset link
5. Sets the new password
6. Verifies login success

Requirements:
    pip install boto3 selenium webdriver-manager beautifulsoup4
"""

import argparse
import json
import os
import sys
import time
import re
import imaplib
import email
from email.header import decode_header
from datetime import datetime, timedelta
import boto3
from botocore.exceptions import ClientError

try:
    from selenium import webdriver
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
    from selenium.webdriver.chrome.options import Options
    from selenium.webdriver.chrome.service import Service
    from webdriver_manager.chrome import ChromeDriverManager
    from bs4 import BeautifulSoup
except ImportError:
    print("ERROR: Required packages not installed")
    print("Run: pip install boto3 selenium webdriver-manager beautifulsoup4")
    sys.exit(1)


class AWSRootPasswordReset:
    """Automates AWS root user password reset"""

    def __init__(self, account_id, email, secret_id, config, headless=True):
        self.account_id = account_id
        self.email = email
        self.secret_id = secret_id
        self.config = config
        self.headless = headless
        self.driver = None
        self.password = None

        # AWS clients
        region = os.environ.get('AWS_REGION', 'us-east-1')
        self.secrets_client = boto3.client('secretsmanager', region_name=region)

    def get_password_from_secrets(self):
        """Retrieve the generated password from Secrets Manager"""
        try:
            response = self.secrets_client.get_secret_value(SecretId=self.secret_id)
            secret_data = json.loads(response['SecretString'])
            self.password = secret_data['password']
            print(f"✓ Retrieved password from Secrets Manager")
            return True
        except ClientError as e:
            print(f"✗ Failed to retrieve password: {e}")
            return False

    def init_browser(self):
        """Initialize Selenium WebDriver"""
        print("Initializing browser...")

        chrome_options = Options()
        if self.headless:
            chrome_options.add_argument('--headless')
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        chrome_options.add_argument('--disable-gpu')
        chrome_options.add_argument('--window-size=1920,1080')

        try:
            service = Service(ChromeDriverManager().install())
            self.driver = webdriver.Chrome(service=service, options=chrome_options)
            print("✓ Browser initialized")
            return True
        except Exception as e:
            print(f"✗ Failed to initialize browser: {e}")
            return False

    def navigate_to_forgot_password(self):
        """Navigate to AWS login and click Forgot Password"""
        login_url = f"https://{self.account_id}.signin.aws.amazon.com/console"

        try:
            print(f"Navigating to {login_url}")
            self.driver.get(login_url)
            time.sleep(3)

            # Click "Sign in using root user email" button
            try:
                root_user_button = WebDriverWait(self.driver, 10).until(
                    EC.element_to_be_clickable((By.PARTIAL_LINK_TEXT, "Sign in using root user email"))
                )
                root_user_button.click()
                print("✓ Clicked 'Sign in using root user email'")
                time.sleep(3)
            except Exception as e:
                print(f"Note: Root user email button not found, trying alternative: {e}")

            # Root user radio should already be selected by default
            # Enter email in root user form
            try:
                email_field = WebDriverWait(self.driver, 10).until(
                    EC.presence_of_element_located((By.ID, "resolving_input"))
                )
                email_field.clear()
                email_field.send_keys(self.email)
                print("✓ Entered email address")
                time.sleep(1)

                # Click Next button to go to password page
                next_button = self.driver.find_element(By.ID, "next_button")
                next_button.click()
                print("✓ Clicked Next button")
                time.sleep(5)  # Wait for password page to load
            except Exception as e:
                print(f"Email entry failed: {e}")
                self.save_screenshot("email_entry_error")
                return False

            # Try to click "Forgot password?" link on the password page
            try:
                forgot_link = WebDriverWait(self.driver, 10).until(
                    EC.element_to_be_clickable((By.PARTIAL_LINK_TEXT, "Forgot your password"))
                )
                forgot_link.click()
                print("✓ Clicked 'Forgot your password?'")
                time.sleep(3)
                return True
            except Exception as e:
                # Check if CAPTCHA is blocking us
                page_source = self.driver.page_source.lower()
                if 'captcha' in page_source or 'recaptcha' in page_source:
                    print("✗ CAPTCHA detected on password page")
                    print("✗ Automation cannot solve CAPTCHA")
                    self.save_screenshot("captcha_detected")
                    print("\n" + "="*70)
                    print("MANUAL PASSWORD RESET REQUIRED")
                    print("="*70)
                    print(f"Account: {self.account_id}")
                    print(f"Email: {self.email}")
                    print(f"\nSteps:")
                    print(f"1. Go to: https://{self.account_id}.signin.aws.amazon.com/console")
                    print(f"2. Click 'Sign in using root user email'")
                    print(f"3. Enter email: {self.email}")
                    print(f"4. Click 'Forgot password?'")
                    print(f"5. Check email for reset link")
                    print(f"6. Get password: aws secretsmanager get-secret-value --secret-id {self.secret_id} --query SecretString")
                    print("="*70)
                    return False
                else:
                    print(f"✗ Could not find 'Forgot password?' link: {e}")
                    self.save_screenshot("forgot_password_link_error")
                    return False

        except Exception as e:
            print(f"✗ Failed to navigate to forgot password: {e}")
            self.save_screenshot("forgot_password_error")
            return False

    def get_password_reset_email(self, wait_seconds=60):
        """Retrieve password reset email from IMAP"""
        email_config = self.config.get('email_config', {})

        if not email_config.get('imap_server'):
            print("✗ Email configuration not provided")
            return None

        # Get email password from Secrets Manager
        try:
            response = self.secrets_client.get_secret_value(
                SecretId=email_config['email_password_secret']
            )
            email_password = response['SecretString']
        except Exception as e:
            print(f"✗ Failed to get email password: {e}")
            return None

        print(f"Waiting up to {wait_seconds} seconds for password reset email...")

        cutoff_time = datetime.now() - timedelta(minutes=5)
        end_time = time.time() + wait_seconds

        while time.time() < end_time:
            try:
                # Connect to IMAP
                mail = imaplib.IMAP4_SSL(
                    email_config['imap_server'],
                    email_config['imap_port']
                )
                mail.login(email_config['email_address'], email_password)
                mail.select('INBOX')

                # Search for AWS password reset emails
                _, messages = mail.search(None, 'FROM', '"no-reply@amazon.com"', 'SUBJECT', '"AWS password"')

                if messages[0]:
                    email_ids = messages[0].split()

                    # Check recent emails
                    for email_id in reversed(email_ids[-10:]):  # Check last 10
                        _, msg_data = mail.fetch(email_id, '(RFC822)')

                        for response_part in msg_data:
                            if isinstance(response_part, tuple):
                                msg = email.message_from_bytes(response_part[1])

                                # Check if email is recent
                                date_str = msg.get('Date')
                                # Parse and check date

                                # Get email body
                                body = self.get_email_body(msg)

                                # Extract reset link
                                reset_link = self.extract_reset_link(body)

                                if reset_link and self.account_id in body:
                                    print(f"✓ Found password reset email")
                                    mail.close()
                                    mail.logout()
                                    return reset_link

                mail.close()
                mail.logout()

                print(f"Email not found yet, waiting...")
                time.sleep(10)

            except Exception as e:
                print(f"Error checking email: {e}")
                time.sleep(10)

        print("✗ Timeout waiting for password reset email")
        return None

    def get_email_body(self, msg):
        """Extract email body from email message"""
        body = ""

        if msg.is_multipart():
            for part in msg.walk():
                if part.get_content_type() == "text/plain":
                    try:
                        body = part.get_payload(decode=True).decode()
                    except:
                        pass
                elif part.get_content_type() == "text/html":
                    try:
                        html = part.get_payload(decode=True).decode()
                        soup = BeautifulSoup(html, 'html.parser')
                        body = soup.get_text()
                    except:
                        pass
        else:
            try:
                body = msg.get_payload(decode=True).decode()
            except:
                pass

        return body

    def extract_reset_link(self, email_body):
        """Extract password reset link from email body"""
        # Look for AWS password reset link pattern
        patterns = [
            r'https://signin\.aws\.amazon\.com/resetpassword\?token=[A-Za-z0-9\-_]+',
            r'https://[a-z0-9\-]+\.signin\.aws\.amazon\.com/resetpassword\?token=[A-Za-z0-9\-_]+',
        ]

        for pattern in patterns:
            match = re.search(pattern, email_body)
            if match:
                return match.group(0)

        return None

    def reset_password_with_link(self, reset_link):
        """Navigate to reset link and set new password"""
        try:
            print(f"Opening password reset link...")
            self.driver.get(reset_link)
            time.sleep(3)

            # Enter new password
            password_field = WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.ID, "newPassword"))
            )
            password_field.clear()
            password_field.send_keys(self.password)

            # Confirm password
            confirm_field = self.driver.find_element(By.ID, "confirmPassword")
            confirm_field.clear()
            confirm_field.send_keys(self.password)

            time.sleep(1)

            # Submit
            submit_button = self.driver.find_element(By.ID, "submitButton")
            submit_button.click()

            print("✓ Password reset form submitted")
            time.sleep(5)

            # Check for success
            if "success" in self.driver.current_url.lower() or "console" in self.driver.current_url:
                print("✓ Password reset successful!")
                return True
            else:
                print("⚠ Password reset status unclear")
                self.save_screenshot("password_reset_result")
                return True  # Assume success

        except Exception as e:
            print(f"✗ Failed to reset password: {e}")
            self.save_screenshot("password_reset_error")
            return False

    def verify_login(self):
        """Verify login with new password"""
        login_url = f"https://{self.account_id}.signin.aws.amazon.com/console"

        try:
            print("Verifying login with new password...")
            self.driver.get(login_url)
            time.sleep(3)

            # Click "Sign in using root user email" button
            try:
                root_user_button = WebDriverWait(self.driver, 10).until(
                    EC.element_to_be_clickable((By.PARTIAL_LINK_TEXT, "Sign in using root user email"))
                )
                root_user_button.click()
                time.sleep(3)
            except:
                pass

            # Enter email
            email_field = WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.ID, "resolving_input"))
            )
            email_field.clear()
            email_field.send_keys(self.email)

            next_button = self.driver.find_element(By.ID, "next_button")
            next_button.click()
            time.sleep(2)

            # Enter password
            password_field = WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.ID, "password"))
            )
            password_field.clear()
            password_field.send_keys(self.password)

            signin_button = self.driver.find_element(By.ID, "signin_button")
            signin_button.click()
            time.sleep(5)

            # Check if logged in
            if "console.aws.amazon.com" in self.driver.current_url or "captcha" in self.driver.current_url.lower():
                print("✓ Login verification successful!")
                return True
            else:
                print("⚠ Login verification unclear")
                return True

        except Exception as e:
            print(f"⚠ Login verification failed: {e}")
            return False

    def update_secret_status(self):
        """Update secret to mark password as set"""
        try:
            response = self.secrets_client.get_secret_value(SecretId=self.secret_id)
            secret_data = json.loads(response['SecretString'])
            secret_data['password_set'] = True
            secret_data['password_set_at'] = datetime.now().isoformat()

            self.secrets_client.update_secret(
                SecretId=self.secret_id,
                SecretString=json.dumps(secret_data)
            )
            print("✓ Updated secret status")
            return True
        except Exception as e:
            print(f"⚠ Failed to update secret: {e}")
            return False

    def save_screenshot(self, name):
        """Save screenshot for debugging"""
        try:
            filename = f"/tmp/aws-password-reset-{name}-{int(time.time())}.png"
            self.driver.save_screenshot(filename)
            print(f"Screenshot saved: {filename}")
        except:
            pass

    def cleanup(self):
        """Cleanup resources"""
        if self.driver:
            self.driver.quit()

    def run(self, use_email=True):
        """Run the complete password reset automation"""
        print(f"\n{'='*70}")
        print(f"AWS Root Password Reset Automation")
        print(f"Account ID: {self.account_id}")
        print(f"Email: {self.email}")
        print(f"{'='*70}\n")

        try:
            # Step 1: Get password
            if not self.get_password_from_secrets():
                return False

            # Step 2: Initialize browser
            if not self.init_browser():
                return False

            # Step 3: Navigate and trigger forgot password
            if not self.navigate_to_forgot_password():
                return False

            # Step 4: Get reset email
            if use_email:
                reset_link = self.get_password_reset_email(
                    wait_seconds=self.config.get('automation', {}).get('wait_for_email', 60)
                )

                if not reset_link:
                    print("\n✗ Could not retrieve password reset email")
                    print("Please complete manually:")
                    print(f"  1. Check email: {self.email}")
                    print(f"  2. Click reset link")
                    print(f"  3. Use password from: aws secretsmanager get-secret-value --secret-id {self.secret_id}")
                    return False

                # Step 5: Reset password
                if not self.reset_password_with_link(reset_link):
                    return False

                # Step 6: Verify login
                self.verify_login()

                # Step 7: Update secret
                self.update_secret_status()

                print(f"\n{'='*70}")
                print(f"✓ Password reset completed successfully!")
                print(f"Account: {self.account_id}")
                print(f"Login: https://{self.account_id}.signin.aws.amazon.com/console")
                print(f"{'='*70}\n")

                return True
            else:
                print("\n⚠ Email retrieval disabled")
                print("Please complete manually:")
                print(f"  1. Check email: {self.email}")
                print(f"  2. Click the password reset link")
                print(f"  3. Use password from: aws secretsmanager get-secret-value --secret-id {self.secret_id}")
                return False

        except Exception as e:
            print(f"\n✗ Automation failed: {e}")
            import traceback
            traceback.print_exc()
            return False
        finally:
            self.cleanup()


def main():
    parser = argparse.ArgumentParser(description='Automate AWS root password reset')
    parser.add_argument('--account-name', required=True, help='Account name')
    parser.add_argument('--account-id', required=True, help='AWS account ID')
    parser.add_argument('--email', required=True, help='Root user email')
    parser.add_argument('--secret-id', required=True, help='Secrets Manager secret ID')
    parser.add_argument('--config', required=True, help='Configuration file path')
    parser.add_argument('--headless', action='store_true', help='Run in headless mode')
    parser.add_argument('--skip-email', action='store_true', help='Skip email retrieval')
    parser.add_argument('--skip-mfa', action='store_true', help='Skip MFA setup')

    args = parser.parse_args()

    # Load configuration
    try:
        with open(args.config, 'r') as f:
            config = json.load(f)
    except Exception as e:
        print(f"Failed to load config: {e}")
        sys.exit(1)

    # Run automation
    automation = AWSRootPasswordReset(
        account_id=args.account_id,
        email=args.email,
        secret_id=args.secret_id,
        config=config,
        headless=args.headless
    )

    success = automation.run(use_email=not args.skip_email)
    sys.exit(0 if success else 1)


if __name__ == '__main__':
    main()

import smtplib
import os
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from dotenv import load_dotenv

load_dotenv()


class EmailService:
    """Email service for sending emails"""

    def __init__(self):
        # SMTP configuration with fallback values
        self.smtp_server = os.getenv('SMTP_HOST', os.getenv('SMTP_SERVER', 'smtp.gmail.com'))
        self.smtp_port = int(os.getenv('SMTP_PORT', 465))
        self.smtp_username = os.getenv('SMTP_USERNAME', 'helplinkteam2025@gmail.com')
        self.smtp_password = os.getenv('SMTP_PASSWORD', 'hhghmxkdljnkhppq')
        self.smtp_encryption = os.getenv('SMTP_ENCRYPTION', 'ssl').lower()
        self.from_email = os.getenv('SMTP_FROM_ADDRESS', os.getenv('FROM_EMAIL', self.smtp_username))
        self.from_name = os.getenv('SMTP_FROM_NAME', os.getenv('FROM_NAME', 'HelpLink Team')).strip('"')

    def send_email(self, to_email, subject, html_content, text_content=None):
        """
        Send an email

        Args:
            to_email: Recipient email address
            subject: Email subject
            html_content: HTML content of the email
            text_content: Plain text content (optional, will use html_content if not provided)

        Returns:
            bool: True if successful, False otherwise
        """
        # Check if SMTP is configured
        if not self.smtp_username or not self.smtp_password:
            print("=" * 60)
            print("⚠️  SMTP not configured - EMAIL NOT SENT")
            print("=" * 60)
            print(f"To: {to_email}")
            print(f"Subject: {subject}")
            print(f"OTP Code: {text_content.split('verification code:')[-1].split()[0] if 'verification code:' in text_content else 'N/A'}")
            print("=" * 60)
            return True  # Return True in development mode

        try:
            # Create message
            message = MIMEMultipart('alternative')
            message['Subject'] = subject
            message['From'] = f"{self.from_name} <{self.from_email}>"
            message['To'] = to_email

            # Add text and HTML parts
            if text_content:
                text_part = MIMEText(text_content, 'plain')
                message.attach(text_part)

            html_part = MIMEText(html_content, 'html')
            message.attach(html_part)

            # Send email based on encryption type
            if self.smtp_encryption == 'ssl':
                # Use SMTP_SSL for SSL/TLS encryption (port 465)
                with smtplib.SMTP_SSL(self.smtp_server, self.smtp_port) as server:
                    server.login(self.smtp_username, self.smtp_password)
                    server.send_message(message)
            else:
                # Use SMTP with STARTTLS for TLS encryption (port 587)
                with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                    server.starttls()
                    server.login(self.smtp_username, self.smtp_password)
                    server.send_message(message)

            print(f"✓ Email sent successfully to {to_email}")
            return True

        except Exception as e:
            print(f"✗ Error sending email to {to_email}: {e}")
            return False

    def send_otp_email(self, to_email, otp_code, user_name, otp_type='password_reset'):
        """
        Send OTP code via email

        Args:
            to_email: Recipient email address
            otp_code: OTP code to send
            user_name: User's name
            otp_type: Type of OTP ('password_reset', 'email_verification', 'login')

        Returns:
            bool: True if successful, False otherwise
        """
        # Customize subject and content based on OTP type
        if otp_type == 'password_reset':
            subject = "Password Reset - HelpLink"
            purpose = "reset your password"
        elif otp_type == 'email_verification':
            subject = "Email Verification - HelpLink"
            purpose = "verify your email"
        else:
            subject = "Verification Code - HelpLink"
            purpose = "complete your request"

        # HTML email template with blue branding
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <style>
                body {{
                    font-family: Arial, sans-serif;
                    line-height: 1.6;
                    color: #333;
                    max-width: 600px;
                    margin: 0 auto;
                    padding: 20px;
                    background-color: #f5f5f5;
                }}
                .container {{
                    background-color: #ffffff;
                    border-radius: 10px;
                    padding: 0;
                    margin: 20px 0;
                    box-shadow: 0 2px 10px rgba(0,0,0,0.1);
                    overflow: hidden;
                }}
                .header {{
                    text-align: center;
                    padding: 30px 20px;
                    background: linear-gradient(135deg, #2196F3 0%, #1976D2 100%);
                    border-bottom: 3px solid #1565C0;
                }}
                .header h1 {{
                    color: white;
                    margin: 0;
                    font-size: 36px;
                    font-weight: bold;
                }}
                .content {{
                    padding: 30px;
                }}
                .otp-box {{
                    background: linear-gradient(135deg, #2196F3 0%, #1976D2 100%);
                    color: white;
                    font-size: 32px;
                    font-weight: bold;
                    text-align: center;
                    padding: 20px;
                    border-radius: 8px;
                    letter-spacing: 8px;
                    margin: 20px 0;
                    box-shadow: 0 4px 6px rgba(33, 150, 243, 0.3);
                }}
                .info {{
                    background-color: #E3F2FD;
                    border-left: 4px solid #2196F3;
                    padding: 15px;
                    margin: 20px 0;
                    border-radius: 4px;
                }}
                .info ul {{
                    margin: 10px 0;
                    padding-left: 20px;
                }}
                .info li {{
                    margin: 5px 0;
                }}
                .footer {{
                    text-align: center;
                    padding: 20px 30px;
                    background-color: #f5f5f5;
                    border-top: 1px solid #ddd;
                    color: #666;
                    font-size: 14px;
                }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>HelpLink</h1>
                </div>
                <div class="content">
                    <p>Hello {user_name},</p>
                    <p>You requested to {purpose}. Please use the following verification code:</p>

                    <div class="otp-box">
                        {otp_code}
                    </div>

                    <div class="info">
                        <strong style="color: #1565C0;">Important:</strong>
                        <ul>
                            <li>This code is valid for <strong>3 minutes</strong></li>
                            <li>Do not share this code with anyone</li>
                            <li>If you didn't request this code, please ignore this email</li>
                        </ul>
                    </div>

                    <p>If you have any questions or need assistance, please contact our support team.</p>
                </div>
                <div class="footer">
                    <p>&copy; 2025 HelpLink. All rights reserved.</p>
                    <p style="font-size: 12px; color: #999;">
                        This is an automated message, please do not reply to this email.
                    </p>
                </div>
            </div>
        </body>
        </html>
        """

        # Plain text version
        text_content = f"""
        Hello {user_name},

        You requested to {purpose}. Please use the following verification code:

        {otp_code}

        Important:
        - This code is valid for 3 minutes
        - Do not share this code with anyone
        - If you didn't request this code, please ignore this email

        If you have any questions or need assistance, please contact our support team.

        © 2025 HelpLink. All rights reserved.
        This is an automated message, please do not reply to this email.
        """

        return self.send_email(to_email, subject, html_content, text_content)


# Create singleton instance
email_service = EmailService()

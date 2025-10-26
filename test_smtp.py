"""
Test SMTP configuration to verify email sending works
"""
import os
from dotenv import load_dotenv
from utils.email_service import email_service

# Load environment variables
load_dotenv()


def test_smtp_connection():
    """Test SMTP connection and email sending"""
    print("=" * 60)
    print("SMTP Configuration Test")
    print("=" * 60)

    # Display current configuration
    print("\nCurrent SMTP Settings:")
    print(f"  Host: {email_service.smtp_server}")
    print(f"  Port: {email_service.smtp_port}")
    print(f"  Username: {email_service.smtp_username}")
    print(f"  Password: {'*' * len(email_service.smtp_password) if email_service.smtp_password else 'Not set'}")
    print(f"  Encryption: {email_service.smtp_encryption}")
    print(f"  From Email: {email_service.from_email}")
    print(f"  From Name: {email_service.from_name}")
    print("=" * 60)

    # Check if SMTP is configured
    if not email_service.smtp_username or not email_service.smtp_password:
        print("\n❌ SMTP not configured!")
        print("Please set SMTP_USERNAME and SMTP_PASSWORD in your .env file")
        return False

    # Get test email
    test_email = input("\nEnter email address to send test to (or press Enter to use SMTP_USERNAME): ").strip()
    if not test_email:
        test_email = email_service.smtp_username

    print(f"\nSending test email to: {test_email}")

    # Send test email
    success = email_service.send_otp_email(
        to_email=test_email,
        otp_code="123456",
        user_name="Test User",
        otp_type="password_reset"
    )

    print("\n" + "=" * 60)
    if success:
        print("✓ Test email sent successfully!")
        print("Check your inbox (and spam folder)")
    else:
        print("✗ Failed to send test email")
        print("Check the error message above")
    print("=" * 60)

    return success


def main():
    """Main function"""
    print("\n🧪 SMTP Test Script for HelpLink API")
    print("This will test your email configuration\n")

    try:
        test_smtp_connection()
    except KeyboardInterrupt:
        print("\n\n⚠️  Test interrupted by user")
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()

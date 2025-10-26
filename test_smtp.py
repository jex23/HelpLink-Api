#!/usr/bin/env python3
"""
Test script to verify SMTP email sending functionality
"""
from utils.email_service import email_service

def test_smtp():
    """Test sending an email via SMTP"""
    print("=" * 60)
    print("Testing SMTP Email Sending")
    print("=" * 60)

    # Test recipient
    test_email = "jamesgalos223@gmail.com"
    test_name = "James Galos"
    test_otp = "123456"

    print(f"\nSending test OTP email to: {test_email}")
    print(f"OTP Code: {test_otp}")
    print("\nAttempting to send email...\n")

    # Send test OTP email
    success = email_service.send_otp_email(
        to_email=test_email,
        otp_code=test_otp,
        user_name=test_name,
        otp_type='password_reset'
    )

    print("\n" + "=" * 60)
    if success:
        print("✓ SUCCESS: Email sent successfully!")
        print(f"✓ Check {test_email} for the test OTP email")
    else:
        print("✗ FAILED: Email sending failed")
        print("✗ Please check SMTP configuration and credentials")
    print("=" * 60)

    return success

if __name__ == "__main__":
    test_smtp()

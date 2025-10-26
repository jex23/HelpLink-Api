"""
Test script for password reset functionality
"""
import requests
import time

# Configuration
BASE_URL = "http://localhost:5001/api/auth"
TEST_EMAIL = "test@example.com"  # Change to a real email in your database
NEW_PASSWORD = "newTestPassword123"


def test_password_reset_flow():
    """Test the complete password reset flow"""
    print("=" * 60)
    print("Testing Password Reset Flow")
    print("=" * 60)

    # Step 1: Request OTP
    print("\n[Step 1] Requesting password reset OTP...")
    response = requests.post(
        f"{BASE_URL}/forgot-password",
        json={"email": TEST_EMAIL}
    )
    print(f"Status Code: {response.status_code}")
    print(f"Response: {response.json()}")

    if response.status_code != 200:
        print("❌ Failed to request OTP")
        return

    print("✓ OTP request successful")
    print("\n📧 Check your email for the OTP code (or console if SMTP not configured)")

    # Get OTP from user
    otp_code = input("\nEnter the OTP code from email: ").strip()

    # Step 2: Verify OTP (optional)
    print("\n[Step 2] Verifying OTP...")
    response = requests.post(
        f"{BASE_URL}/verify-otp",
        json={
            "email": TEST_EMAIL,
            "otp_code": otp_code,
            "otp_type": "password_reset"
        }
    )
    print(f"Status Code: {response.status_code}")
    print(f"Response: {response.json()}")

    if response.status_code != 200:
        print("❌ OTP verification failed")
        return

    print("✓ OTP verified successfully")

    # Step 3: Reset password
    print(f"\n[Step 3] Resetting password to: {NEW_PASSWORD}")
    response = requests.post(
        f"{BASE_URL}/reset-password",
        json={
            "email": TEST_EMAIL,
            "otp_code": otp_code,
            "new_password": NEW_PASSWORD
        }
    )
    print(f"Status Code: {response.status_code}")
    print(f"Response: {response.json()}")

    if response.status_code != 200:
        print("❌ Password reset failed")
        return

    print("✓ Password reset successful")

    # Step 4: Login with new password
    print("\n[Step 4] Testing login with new password...")
    response = requests.post(
        f"{BASE_URL}/login",
        json={
            "email": TEST_EMAIL,
            "password": NEW_PASSWORD
        }
    )
    print(f"Status Code: {response.status_code}")
    print(f"Response: {response.json()}")

    if response.status_code != 200:
        print("❌ Login with new password failed")
        return

    print("✓ Login successful with new password")
    print("\n" + "=" * 60)
    print("✓ All tests passed!")
    print("=" * 60)


def test_expired_otp():
    """Test that expired OTPs are rejected"""
    print("\n" + "=" * 60)
    print("Testing Expired OTP")
    print("=" * 60)

    # Request OTP
    print("\n[Step 1] Requesting OTP...")
    response = requests.post(
        f"{BASE_URL}/forgot-password",
        json={"email": TEST_EMAIL}
    )

    if response.status_code != 200:
        print("❌ Failed to request OTP")
        return

    otp_code = input("\nEnter the OTP code: ").strip()

    # Wait for OTP to expire (3 minutes + buffer)
    print("\n⏳ Waiting for OTP to expire (3 minutes + 10 seconds)...")
    time.sleep(190)  # 3 minutes 10 seconds

    # Try to use expired OTP
    print("\n[Step 2] Attempting to use expired OTP...")
    response = requests.post(
        f"{BASE_URL}/reset-password",
        json={
            "email": TEST_EMAIL,
            "otp_code": otp_code,
            "new_password": "somePassword123"
        }
    )
    print(f"Status Code: {response.status_code}")
    print(f"Response: {response.json()}")

    if response.status_code == 401:
        print("✓ Expired OTP correctly rejected")
    else:
        print("❌ Expired OTP should have been rejected")


def test_invalid_otp():
    """Test that invalid OTPs are rejected"""
    print("\n" + "=" * 60)
    print("Testing Invalid OTP")
    print("=" * 60)

    print("\n[Step 1] Attempting to use invalid OTP...")
    response = requests.post(
        f"{BASE_URL}/reset-password",
        json={
            "email": TEST_EMAIL,
            "otp_code": "999999",  # Invalid OTP
            "new_password": "somePassword123"
        }
    )
    print(f"Status Code: {response.status_code}")
    print(f"Response: {response.json()}")

    if response.status_code == 401:
        print("✓ Invalid OTP correctly rejected")
    else:
        print("❌ Invalid OTP should have been rejected")


def test_reused_otp():
    """Test that used OTPs cannot be reused"""
    print("\n" + "=" * 60)
    print("Testing OTP Reuse Prevention")
    print("=" * 60)

    # Request OTP
    print("\n[Step 1] Requesting OTP...")
    response = requests.post(
        f"{BASE_URL}/forgot-password",
        json={"email": TEST_EMAIL}
    )

    if response.status_code != 200:
        print("❌ Failed to request OTP")
        return

    otp_code = input("\nEnter the OTP code: ").strip()

    # Use OTP once
    print("\n[Step 2] Using OTP for first time...")
    response = requests.post(
        f"{BASE_URL}/reset-password",
        json={
            "email": TEST_EMAIL,
            "otp_code": otp_code,
            "new_password": "firstPassword123"
        }
    )

    if response.status_code != 200:
        print("❌ First use failed")
        return

    print("✓ First use successful")

    # Try to reuse OTP
    print("\n[Step 3] Attempting to reuse same OTP...")
    response = requests.post(
        f"{BASE_URL}/reset-password",
        json={
            "email": TEST_EMAIL,
            "otp_code": otp_code,
            "new_password": "secondPassword123"
        }
    )
    print(f"Status Code: {response.status_code}")
    print(f"Response: {response.json()}")

    if response.status_code == 401:
        print("✓ OTP reuse correctly prevented")
    else:
        print("❌ OTP reuse should have been prevented")


def test_email_not_found():
    """Test that non-existent emails don't reveal information"""
    print("\n" + "=" * 60)
    print("Testing Email Enumeration Prevention")
    print("=" * 60)

    print("\n[Step 1] Requesting OTP for non-existent email...")
    response = requests.post(
        f"{BASE_URL}/forgot-password",
        json={"email": "nonexistent@example.com"}
    )
    print(f"Status Code: {response.status_code}")
    print(f"Response: {response.json()}")

    if response.status_code == 200:
        print("✓ Same response for non-existent email (prevents enumeration)")
    else:
        print("❌ Should return success to prevent email enumeration")


def main():
    """Main test runner"""
    print("\n🧪 Password Reset Test Suite")
    print("Make sure the API server is running at:", BASE_URL)
    print("Using test email:", TEST_EMAIL)

    while True:
        print("\n" + "=" * 60)
        print("Select a test to run:")
        print("=" * 60)
        print("1. Complete password reset flow")
        print("2. Test expired OTP rejection")
        print("3. Test invalid OTP rejection")
        print("4. Test OTP reuse prevention")
        print("5. Test email enumeration prevention")
        print("6. Run all tests")
        print("0. Exit")
        print("=" * 60)

        choice = input("\nEnter your choice: ").strip()

        try:
            if choice == "1":
                test_password_reset_flow()
            elif choice == "2":
                test_expired_otp()
            elif choice == "3":
                test_invalid_otp()
            elif choice == "4":
                test_reused_otp()
            elif choice == "5":
                test_email_not_found()
            elif choice == "6":
                test_password_reset_flow()
                test_invalid_otp()
                test_email_not_found()
                print("\n⚠️  Skipping time-dependent tests (expired OTP, reuse)")
                print("Run tests 2 and 4 individually to test these")
            elif choice == "0":
                print("\nExiting test suite. Goodbye!")
                break
            else:
                print("\n❌ Invalid choice. Please try again.")
        except KeyboardInterrupt:
            print("\n\n⚠️  Test interrupted by user")
        except Exception as e:
            print(f"\n❌ Error: {e}")

        input("\nPress Enter to continue...")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nExiting...")

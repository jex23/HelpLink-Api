#!/usr/bin/env python3
"""
Test script to register a user with image upload
"""

import requests
import sys
import json
import time

BASE_URL = "http://localhost:5001"

def wait_for_server(max_attempts=10):
    """Wait for server to be ready"""
    print("Waiting for server to start...")
    for i in range(max_attempts):
        try:
            response = requests.get(f"{BASE_URL}/health", timeout=2)
            if response.status_code == 200:
                print("✅ Server is ready!")
                return True
        except requests.exceptions.RequestException:
            pass
        time.sleep(1)
        print(f"  Attempt {i+1}/{max_attempts}...")
    return False

def register_user_with_image(image_path):
    """Register a new user with image upload"""
    print("\n" + "="*60)
    print("Testing User Registration with Image Upload")
    print("="*60)

    # Prepare user data
    data = {
        'first_name': 'Test',
        'last_name': 'User',
        'email': 'testuser@example.com',
        'password': 'SecurePassword123!',
        'age': '28',
        'account_type': 'beneficiary',
        'address': '123 Test Street, Test City',
        'number': '+639123456789'
    }

    # Prepare file
    files = {}
    if image_path:
        try:
            files['profile_image'] = open(image_path, 'rb')
            print(f"\n📎 Uploading image: {image_path}")
        except FileNotFoundError:
            print(f"❌ Error: Image file not found at {image_path}")
            return None

    print(f"\n📝 User Details:")
    print(f"  Name: {data['first_name']} {data['last_name']}")
    print(f"  Email: {data['email']}")
    print(f"  Account Type: {data['account_type']}")

    # Make request
    print(f"\n🚀 Sending registration request to {BASE_URL}/api/auth/register...")

    try:
        response = requests.post(
            f"{BASE_URL}/api/auth/register",
            data=data,
            files=files if files else None,
            timeout=30
        )

        # Close file if opened
        if files:
            files['profile_image'].close()

        print(f"\n📊 Response Status: {response.status_code}")

        if response.status_code == 201:
            result = response.json()
            print("\n✅ Registration Successful!")
            print("\n👤 User Information:")
            user = result.get('user', {})
            for key, value in user.items():
                if key != 'password_hash':
                    print(f"  {key}: {value}")

            token = result.get('token')
            if token:
                print(f"\n🔑 JWT Token: {token[:50]}...")

            # Save token to file for future use
            with open('test_token.txt', 'w') as f:
                f.write(token)
            print("\n💾 Token saved to test_token.txt")

            return result

        elif response.status_code == 409:
            print("\n⚠️  User already exists. Attempting login instead...")
            return login_user(data['email'], data['password'])

        else:
            print(f"\n❌ Registration Failed!")
            try:
                error_data = response.json()
                print(f"Error: {json.dumps(error_data, indent=2)}")
            except:
                print(f"Response: {response.text}")
            return None

    except requests.exceptions.RequestException as e:
        print(f"\n❌ Request Error: {e}")
        return None

def login_user(email, password):
    """Login user if already registered"""
    print(f"\n🔐 Attempting to login with {email}...")

    data = {
        'email': email,
        'password': password
    }

    try:
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json=data,
            headers={'Content-Type': 'application/json'},
            timeout=10
        )

        if response.status_code == 200:
            result = response.json()
            print("\n✅ Login Successful!")

            user = result.get('user', {})
            print("\n👤 User Information:")
            for key, value in user.items():
                print(f"  {key}: {value}")

            token = result.get('token')
            if token:
                print(f"\n🔑 JWT Token: {token[:50]}...")
                with open('test_token.txt', 'w') as f:
                    f.write(token)
                print("💾 Token saved to test_token.txt")

            return result
        else:
            print(f"❌ Login Failed: {response.status_code}")
            print(response.text)
            return None

    except requests.exceptions.RequestException as e:
        print(f"❌ Request Error: {e}")
        return None

def test_authenticated_endpoint():
    """Test the /api/auth/me endpoint"""
    print("\n" + "="*60)
    print("Testing Authenticated Endpoint (/api/auth/me)")
    print("="*60)

    try:
        with open('test_token.txt', 'r') as f:
            token = f.read().strip()

        print(f"\n🔑 Using token from test_token.txt")

        response = requests.get(
            f"{BASE_URL}/api/auth/me",
            headers={'Authorization': f'Bearer {token}'},
            timeout=10
        )

        print(f"📊 Response Status: {response.status_code}")

        if response.status_code == 200:
            result = response.json()
            print("\n✅ Authentication Successful!")
            print("\n👤 Current User:")
            user = result.get('user', {})
            for key, value in user.items():
                print(f"  {key}: {value}")
        else:
            print(f"❌ Authentication Failed")
            print(response.text)

    except FileNotFoundError:
        print("❌ No token file found. Please register/login first.")
    except requests.exceptions.RequestException as e:
        print(f"❌ Request Error: {e}")

if __name__ == "__main__":
    print("="*60)
    print("HelpLink API - Registration Test with Image Upload")
    print("="*60)

    # Check if image path provided
    image_path = sys.argv[1] if len(sys.argv) > 1 else None

    if not image_path:
        print("\n⚠️  No image path provided")
        print("Usage: python3 test_registration_with_image.py <image_path>")
        print("\nProceeding with registration without image...")

    # Wait for server
    if not wait_for_server():
        print("\n❌ Server is not running. Please start it with: python3 app.py")
        sys.exit(1)

    # Test registration
    result = register_user_with_image(image_path)

    if result:
        # Test authenticated endpoint
        test_authenticated_endpoint()
        print("\n" + "="*60)
        print("✅ All tests completed successfully!")
        print("="*60)
    else:
        print("\n" + "="*60)
        print("❌ Tests failed")
        print("="*60)
        sys.exit(1)

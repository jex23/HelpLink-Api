#!/usr/bin/env python3
"""
Simple test script to verify the API setup
Run this after starting the API with: python app.py
"""

import requests
import json

BASE_URL = "http://localhost:5000"

def test_health():
    """Test health endpoint"""
    print("Testing /health endpoint...")
    response = requests.get(f"{BASE_URL}/health")
    print(f"Status: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2)}")
    print("-" * 50)

def test_home():
    """Test home endpoint"""
    print("Testing / endpoint...")
    response = requests.get(f"{BASE_URL}/")
    print(f"Status: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2)}")
    print("-" * 50)

def test_register():
    """Test registration endpoint"""
    print("Testing /api/auth/register endpoint...")

    # Prepare test data
    data = {
        'first_name': 'John',
        'last_name': 'Doe',
        'email': 'john.doe@example.com',
        'password': 'SecurePassword123!',
        'age': '25',
        'account_type': 'beneficiary',
        'address': '123 Main St, City',
        'number': '+1234567890'
    }

    response = requests.post(f"{BASE_URL}/api/auth/register", data=data)
    print(f"Status: {response.status_code}")

    if response.status_code == 201:
        result = response.json()
        print(f"Success! User created with ID: {result['user']['id']}")
        print(f"Token: {result['token'][:50]}...")
        return result['token']
    else:
        print(f"Response: {json.dumps(response.json(), indent=2)}")

    print("-" * 50)
    return None

def test_login():
    """Test login endpoint"""
    print("Testing /api/auth/login endpoint...")

    data = {
        'email': 'john.doe@example.com',
        'password': 'SecurePassword123!'
    }

    response = requests.post(
        f"{BASE_URL}/api/auth/login",
        json=data,
        headers={'Content-Type': 'application/json'}
    )

    print(f"Status: {response.status_code}")

    if response.status_code == 200:
        result = response.json()
        print(f"Success! Logged in as: {result['user']['email']}")
        print(f"Token: {result['token'][:50]}...")
        return result['token']
    else:
        print(f"Response: {json.dumps(response.json(), indent=2)}")

    print("-" * 50)
    return None

def test_me(token):
    """Test get current user endpoint"""
    print("Testing /api/auth/me endpoint...")

    response = requests.get(
        f"{BASE_URL}/api/auth/me",
        headers={'Authorization': f'Bearer {token}'}
    )

    print(f"Status: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2)}")
    print("-" * 50)

if __name__ == "__main__":
    print("=" * 50)
    print("HelpLink API Test Suite")
    print("=" * 50)
    print()

    try:
        # Test basic endpoints
        test_health()
        test_home()

        # Test authentication flow
        token = test_register()

        if not token:
            print("Registration failed, trying login...")
            token = test_login()

        if token:
            test_me(token)
            print("\n✅ All tests completed!")
        else:
            print("\n❌ Authentication tests failed")

    except requests.exceptions.ConnectionError:
        print("❌ Error: Could not connect to API. Make sure the server is running:")
        print("   python app.py")
    except Exception as e:
        print(f"❌ Error: {e}")

from flask import Blueprint, request, jsonify, current_app
import jwt
from datetime import datetime, timedelta, timezone
from functools import wraps

from models.auth_model import AuthModel
from utils.r2_storage import r2_storage
from utils.email_service import email_service

auth_bp = Blueprint('auth', __name__)

# Allowed file extensions
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}

def allowed_file(filename):
    """Check if file extension is allowed"""
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def process_user_images(user_data):
    """
    Convert image paths to full URLs using R2 storage presigned URLs

    Args:
        user_data: Dictionary containing user information

    Returns:
        Dictionary with image paths converted to full URLs
    """
    if not user_data:
        return user_data

    # Make a copy to avoid modifying the original
    user = dict(user_data)

    # Image fields to process
    image_fields = ['profile_image', 'verification_selfie', 'valid_id']

    # Convert each image path to a full URL
    for field in image_fields:
        if field in user and user[field]:
            # Generate presigned URL (valid for 7 days)
            url = r2_storage.get_file_url(user[field], expiration=604800)
            if url:
                user[field] = url

    return user

def token_required(f):
    """Decorator to protect routes with JWT authentication"""
    @wraps(f)
    def decorated(*args, **kwargs):
        token = None

        # Get token from header
        if 'Authorization' in request.headers:
            auth_header = request.headers['Authorization']
            try:
                token = auth_header.split(' ')[1]  # Bearer <token>
            except IndexError:
                return jsonify({'error': 'Invalid token format'}), 401

        if not token:
            return jsonify({'error': 'Token is missing'}), 401

        try:
            # Decode token
            data = jwt.decode(
                token,
                current_app.config['SECRET_KEY'],
                algorithms=['HS256']
            )
            current_user_id = data['user_id']

            # Get database connection
            from app import get_db_connection
            conn = get_db_connection()

            # Get current user
            current_user = AuthModel.get_user_by_id(conn, current_user_id)

            if not current_user:
                return jsonify({'error': 'User not found'}), 401

        except jwt.ExpiredSignatureError:
            return jsonify({'error': 'Token has expired'}), 401
        except jwt.InvalidTokenError:
            return jsonify({'error': 'Invalid token'}), 401
        except Exception as e:
            return jsonify({'error': str(e)}), 401

        return f(current_user, *args, **kwargs)

    return decorated

@auth_bp.route('/register', methods=['POST'])
def register():
    """
    Register a new user with optional file uploads

    Form data:
        - first_name (required)
        - last_name (required)
        - email (required)
        - password (required)
        - address (optional)
        - age (optional)
        - number (optional)
        - account_type (optional, default: beneficiary)
        - profile_image (file, optional)
        - verification_selfie (file, optional)
        - valid_id (file, optional)
    """
    try:
        # Get form data
        first_name = request.form.get('first_name')
        last_name = request.form.get('last_name')
        email = request.form.get('email')
        password = request.form.get('password')
        address = request.form.get('address')
        age = request.form.get('age')
        number = request.form.get('number')
        account_type = request.form.get('account_type', 'beneficiary')

        # Validate required fields
        if not all([first_name, last_name, email, password]):
            return jsonify({
                'error': 'Missing required fields',
                'required': ['first_name', 'last_name', 'email', 'password']
            }), 400

        # Get database connection
        from app import get_db_connection
        conn = get_db_connection()

        # Check if user already exists
        existing_user = AuthModel.get_user_by_email(conn, email)
        if existing_user:
            return jsonify({'error': 'Email already registered'}), 409

        # Handle file uploads (R2 storage already initialized in app.py)
        profile_image_path = None
        verification_selfie_path = None
        valid_id_path = None

        # Upload profile image
        if 'profile_image' in request.files:
            profile_image = request.files['profile_image']
            print(f"Profile image received: {profile_image.filename}")
            if profile_image and profile_image.filename != '' and allowed_file(profile_image.filename):
                profile_image_path = r2_storage.upload_file(profile_image, 'profiles')
                print(f"Profile image uploaded to: {profile_image_path}")
            elif profile_image and profile_image.filename != '':
                print(f"Profile image file type not allowed: {profile_image.filename}")

        # Upload verification selfie
        if 'verification_selfie' in request.files:
            verification_selfie = request.files['verification_selfie']
            print(f"Verification selfie received: {verification_selfie.filename}")
            if verification_selfie and verification_selfie.filename != '' and allowed_file(verification_selfie.filename):
                verification_selfie_path = r2_storage.upload_file(
                    verification_selfie,
                    'verifications/selfies'
                )
                print(f"Verification selfie uploaded to: {verification_selfie_path}")
            elif verification_selfie and verification_selfie.filename != '':
                print(f"Verification selfie file type not allowed: {verification_selfie.filename}")

        # Upload valid ID
        if 'valid_id' in request.files:
            valid_id = request.files['valid_id']
            print(f"Valid ID received: {valid_id.filename}")
            if valid_id and valid_id.filename != '' and allowed_file(valid_id.filename):
                valid_id_path = r2_storage.upload_file(valid_id, 'verifications/ids')
                print(f"Valid ID uploaded to: {valid_id_path}")
            elif valid_id and valid_id.filename != '':
                print(f"Valid ID file type not allowed: {valid_id.filename}")

        # Hash password
        password_hash = AuthModel.hash_password(password)

        # Prepare user data
        user_data = {
            'first_name': first_name,
            'last_name': last_name,
            'email': email,
            'password_hash': password_hash,
            'address': address,
            'age': int(age) if age else None,
            'number': number,
            'account_type': account_type,
            'badge': 'under_review',
            'profile_image': profile_image_path,
            'verification_selfie': verification_selfie_path,
            'valid_id': valid_id_path
        }

        # Create user
        user_id = AuthModel.create_user(conn, user_data)

        if not user_id:
            return jsonify({'error': 'Failed to create user'}), 500

        # Get created user
        user = AuthModel.get_user_by_id(conn, user_id)

        # Remove password hash from response
        if user and 'password_hash' in user:
            del user['password_hash']

        # Process user images to return full URLs
        user = process_user_images(user)

        # Generate JWT token
        token = jwt.encode({
            'user_id': user_id,
            'email': email,
            'exp': datetime.now(timezone.utc) + timedelta(days=30)
        }, current_app.config['SECRET_KEY'], algorithm='HS256')

        return jsonify({
            'message': 'User registered successfully',
            'user': user,
            'token': token
        }), 201

    except Exception as e:
        print(f"Registration error: {e}")
        return jsonify({'error': 'Registration failed', 'details': str(e)}), 500

@auth_bp.route('/login', methods=['POST'])
def login():
    """
    Login user and return JWT token

    JSON body:
        - email (required)
        - password (required)
    """
    try:
        data = request.get_json()

        if not data:
            return jsonify({'error': 'No data provided'}), 400

        email = data.get('email')
        password = data.get('password')

        # Validate required fields
        if not all([email, password]):
            return jsonify({
                'error': 'Missing required fields',
                'required': ['email', 'password']
            }), 400

        # Get database connection
        from app import get_db_connection
        conn = get_db_connection()

        # Get user by email
        user = AuthModel.get_user_by_email(conn, email)

        if not user:
            return jsonify({'error': 'Invalid credentials'}), 401

        # Verify password
        if not AuthModel.verify_password(password, user['password_hash']):
            return jsonify({'error': 'Invalid credentials'}), 401

        # Update last logon
        AuthModel.update_last_logon(conn, user['id'])

        # Get updated user data
        user = AuthModel.get_user_by_id(conn, user['id'])

        # Remove password hash from response
        if 'password_hash' in user:
            del user['password_hash']

        # Process user images to return full URLs
        user = process_user_images(user)

        # Generate JWT token
        token = jwt.encode({
            'user_id': user['id'],
            'email': user['email'],
            'exp': datetime.now(timezone.utc) + timedelta(days=30)
        }, current_app.config['SECRET_KEY'], algorithm='HS256')

        return jsonify({
            'message': 'Login successful',
            'user': user,
            'token': token
        }), 200

    except Exception as e:
        print(f"Login error: {e}")
        return jsonify({'error': 'Login failed', 'details': str(e)}), 500

@auth_bp.route('/me', methods=['GET'])
@token_required
def get_current_user(current_user):
    """
    Get current authenticated user information
    Requires Authorization header with Bearer token
    """
    try:
        # Remove password hash from response
        user_data = dict(current_user)
        if 'password_hash' in user_data:
            del user_data['password_hash']

        # Process user images to return full URLs
        user_data = process_user_images(user_data)

        return jsonify({
            'user': user_data
        }), 200

    except Exception as e:
        print(f"Get user error: {e}")
        return jsonify({'error': 'Failed to get user', 'details': str(e)}), 500

@auth_bp.route('/file-url/<path:file_path>', methods=['GET'])
@token_required
def get_file_url(_current_user, file_path):
    """
    Get presigned URL for accessing a file from R2 storage
    Requires Authorization header with Bearer token
    """
    try:
        # Generate presigned URL (valid for 1 hour, R2 storage already initialized in app.py)
        url = r2_storage.get_file_url(file_path, expiration=3600)

        if not url:
            return jsonify({'error': 'Failed to generate URL'}), 500

        return jsonify({
            'url': url,
            'expires_in': 3600
        }), 200

    except Exception as e:
        print(f"Get file URL error: {e}")
        return jsonify({'error': 'Failed to generate URL', 'details': str(e)}), 500

@auth_bp.route('/profile', methods=['PUT'])
@token_required
def update_profile(current_user):
    """
    Update user profile information (excluding email)
    Requires Authorization header with Bearer token

    JSON body:
        - first_name (optional)
        - last_name (optional)
        - address (optional)
        - age (optional)
        - number (optional)
    """
    try:
        data = request.get_json()

        if not data:
            return jsonify({'error': 'No data provided'}), 400

        # Allowed fields to update (excluding email, password, badge, etc.)
        allowed_fields = ['first_name', 'last_name', 'address', 'age', 'number']
        update_data = {}

        for field in allowed_fields:
            if field in data:
                # Convert age to int if provided
                if field == 'age' and data[field] is not None:
                    try:
                        update_data[field] = int(data[field])
                    except (ValueError, TypeError):
                        return jsonify({'error': f'Invalid value for {field}'}), 400
                else:
                    update_data[field] = data[field]

        if not update_data:
            return jsonify({'error': 'No valid fields to update'}), 400

        # Get database connection
        from app import get_db_connection
        conn = get_db_connection()

        # Update user profile
        success = AuthModel.update_user(conn, current_user['id'], update_data)

        if not success:
            return jsonify({'error': 'Failed to update profile'}), 500

        # Get updated user
        updated_user = AuthModel.get_user_by_id(conn, current_user['id'])

        # Remove password hash from response
        if updated_user and 'password_hash' in updated_user:
            del updated_user['password_hash']

        # Process user images to return full URLs
        updated_user = process_user_images(updated_user)

        return jsonify({
            'message': 'Profile updated successfully',
            'user': updated_user
        }), 200

    except Exception as e:
        print(f"Update profile error: {e}")
        return jsonify({'error': 'Failed to update profile', 'details': str(e)}), 500

@auth_bp.route('/change-password', methods=['PUT'])
@token_required
def change_password(current_user):
    """
    Change user's password
    Requires Authorization header with Bearer token

    JSON body:
        - old_password (required)
        - new_password (required)
    """
    try:
        data = request.get_json()

        if not data:
            return jsonify({'error': 'No data provided'}), 400

        old_password = data.get('old_password')
        new_password = data.get('new_password')

        # Validate required fields
        if not all([old_password, new_password]):
            return jsonify({
                'error': 'Missing required fields',
                'required': ['old_password', 'new_password']
            }), 400

        # Verify old password
        if not AuthModel.verify_password(old_password, current_user['password_hash']):
            return jsonify({'error': 'Current password is incorrect'}), 401

        # Validate new password length
        if len(new_password) < 6:
            return jsonify({'error': 'New password must be at least 6 characters long'}), 400

        # Hash new password
        new_password_hash = AuthModel.hash_password(new_password)

        # Get database connection
        from app import get_db_connection
        conn = get_db_connection()

        # Update password
        success = AuthModel.update_user(conn, current_user['id'], {
            'password_hash': new_password_hash
        })

        if not success:
            return jsonify({'error': 'Failed to update password'}), 500

        return jsonify({
            'message': 'Password changed successfully'
        }), 200

    except Exception as e:
        print(f"Change password error: {e}")
        return jsonify({'error': 'Failed to change password', 'details': str(e)}), 500

@auth_bp.route('/forgot-password', methods=['POST'])
def forgot_password():
    """
    Request password reset OTP
    Retrieves user email from database and sends OTP code

    JSON body:
        - email (required)
    """
    try:
        data = request.get_json()

        if not data:
            return jsonify({'error': 'No data provided'}), 400

        email = data.get('email')

        if not email:
            return jsonify({'error': 'Email is required'}), 400

        # Normalize email
        email = email.lower().strip()

        # Get database connection
        from app import get_db_connection
        conn = get_db_connection()

        # Get user by email from database
        print(f"[Password Reset] Looking up user with email: {email}")
        user = AuthModel.get_user_by_email(conn, email)

        if not user:
            # Don't reveal if email exists or not for security
            print(f"[Password Reset] No user found with email: {email}")
            return jsonify({
                'message': 'If the email exists, an OTP has been sent to it'
            }), 200

        # User found - log details (without sensitive info)
        print(f"[Password Reset] User found - ID: {user['id']}, Name: {user['first_name']} {user['last_name']}")
        print(f"[Password Reset] Sending OTP to email retrieved from database: {user['email']}")

        # Create OTP
        otp_code = AuthModel.create_otp(conn, user['id'], otp_type='password_reset', validity_minutes=3)

        if not otp_code:
            print(f"[Password Reset] Failed to generate OTP for user ID: {user['id']}")
            return jsonify({'error': 'Failed to generate OTP'}), 500

        print(f"[Password Reset] OTP generated successfully for user ID: {user['id']}")

        # Send OTP via email using the email from database
        user_name = f"{user['first_name']} {user['last_name']}"
        user_email = user['email']  # Email retrieved from users table

        email_sent = email_service.send_otp_email(
            to_email=user_email,
            otp_code=otp_code,
            user_name=user_name,
            otp_type='password_reset'
        )

        if not email_sent:
            print(f"[Password Reset] Warning: Failed to send OTP email to {user_email}")
            # Still return success to not reveal if email exists
        else:
            print(f"[Password Reset] OTP email sent successfully to {user_email}")

        return jsonify({
            'message': 'If the email exists, an OTP has been sent to it',
            'email': email
        }), 200

    except Exception as e:
        print(f"[Password Reset] Error in forgot_password: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': 'Failed to process request', 'details': str(e)}), 500

@auth_bp.route('/verify-otp', methods=['POST'])
def verify_otp():
    """
    Verify OTP code
    Retrieves user from database and validates OTP

    JSON body:
        - email (required)
        - otp_code (required)
        - otp_type (optional, default: 'password_reset')
    """
    try:
        data = request.get_json()

        if not data:
            return jsonify({'error': 'No data provided'}), 400

        email = data.get('email')
        otp_code = data.get('otp_code')
        otp_type = data.get('otp_type', 'password_reset')

        if not all([email, otp_code]):
            return jsonify({
                'error': 'Missing required fields',
                'required': ['email', 'otp_code']
            }), 400

        # Normalize email
        email = email.lower().strip()

        # Get database connection
        from app import get_db_connection
        conn = get_db_connection()

        # Get user by email from database
        print(f"[OTP Verify] Looking up user with email: {email}")
        user = AuthModel.get_user_by_email(conn, email)

        if not user:
            print(f"[OTP Verify] No user found with email: {email}")
            return jsonify({'error': 'Invalid OTP code'}), 401

        print(f"[OTP Verify] User found - ID: {user['id']}, verifying OTP...")

        # Verify OTP
        otp_record = AuthModel.verify_otp(conn, user['id'], otp_code, otp_type)

        if not otp_record:
            print(f"[OTP Verify] Invalid or expired OTP for user ID: {user['id']}")
            return jsonify({'error': 'Invalid or expired OTP code'}), 401

        print(f"[OTP Verify] OTP verified successfully for user ID: {user['id']}")

        return jsonify({
            'message': 'OTP verified successfully',
            'email': email,
            'otp_valid': True
        }), 200

    except Exception as e:
        print(f"[OTP Verify] Error: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': 'Failed to verify OTP', 'details': str(e)}), 500

@auth_bp.route('/reset-password', methods=['POST'])
def reset_password():
    """
    Reset password using OTP
    Retrieves user from database, verifies OTP, and updates password

    JSON body:
        - email (required)
        - otp_code (required)
        - new_password (required)
    """
    try:
        data = request.get_json()

        if not data:
            return jsonify({'error': 'No data provided'}), 400

        email = data.get('email')
        otp_code = data.get('otp_code')
        new_password = data.get('new_password')

        if not all([email, otp_code, new_password]):
            return jsonify({
                'error': 'Missing required fields',
                'required': ['email', 'otp_code', 'new_password']
            }), 400

        # Validate new password length
        if len(new_password) < 6:
            return jsonify({'error': 'New password must be at least 6 characters long'}), 400

        # Normalize email
        email = email.lower().strip()

        # Get database connection
        from app import get_db_connection
        conn = get_db_connection()

        # Get user by email from database
        print(f"[Password Reset] Looking up user with email: {email}")
        user = AuthModel.get_user_by_email(conn, email)

        if not user:
            print(f"[Password Reset] No user found with email: {email}")
            return jsonify({'error': 'Invalid OTP code'}), 401

        print(f"[Password Reset] User found - ID: {user['id']}, Email: {user['email']}")

        # Verify OTP
        print(f"[Password Reset] Verifying OTP for user ID: {user['id']}")
        otp_record = AuthModel.verify_otp(conn, user['id'], otp_code, 'password_reset')

        if not otp_record:
            print(f"[Password Reset] Invalid or expired OTP for user ID: {user['id']}")
            return jsonify({'error': 'Invalid or expired OTP code'}), 401

        print(f"[Password Reset] OTP verified, updating password for user ID: {user['id']}")

        # Hash new password
        new_password_hash = AuthModel.hash_password(new_password)

        # Update password in database
        success = AuthModel.update_user(conn, user['id'], {
            'password_hash': new_password_hash
        })

        if not success:
            print(f"[Password Reset] Failed to update password in database for user ID: {user['id']}")
            return jsonify({'error': 'Failed to update password'}), 500

        print(f"[Password Reset] Password updated successfully for user ID: {user['id']}")

        # Mark OTP as used
        AuthModel.mark_otp_as_used(conn, otp_record['id'])
        print(f"[Password Reset] OTP marked as used (ID: {otp_record['id']})")

        # Invalidate all other active OTPs for this user
        AuthModel.invalidate_user_otps(conn, user['id'])
        print(f"[Password Reset] All active OTPs invalidated for user ID: {user['id']}")

        print(f"[Password Reset] Password reset completed successfully for {user['email']}")

        return jsonify({
            'message': 'Password reset successfully',
            'email': email
        }), 200

    except Exception as e:
        print(f"[Password Reset] Error in reset_password: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': 'Failed to reset password', 'details': str(e)}), 500

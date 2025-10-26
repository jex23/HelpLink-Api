from flask import Blueprint, request, jsonify, current_app
import jwt
from functools import wraps

from models.auth_model import AuthModel
from utils.r2_storage import r2_storage

credentials_bp = Blueprint('credentials', __name__)

# Allowed file extensions
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}

def allowed_file(filename):
    """Check if file extension is allowed"""
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

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

@credentials_bp.route('/credentials', methods=['GET'])
@token_required
def get_credentials(current_user):
    """
    Get user's credentials (verification_selfie and valid_id)
    Requires Authorization header with Bearer token

    Returns presigned URLs for the credential images
    """
    try:
        user_credentials = {}

        # Get verification_selfie URL if exists
        if current_user.get('verification_selfie'):
            url = r2_storage.get_file_url(current_user['verification_selfie'], expiration=604800)
            if url:
                user_credentials['verification_selfie'] = url

        # Get valid_id URL if exists
        if current_user.get('valid_id'):
            url = r2_storage.get_file_url(current_user['valid_id'], expiration=604800)
            if url:
                user_credentials['valid_id'] = url

        return jsonify({
            'credentials': user_credentials
        }), 200

    except Exception as e:
        print(f"Get credentials error: {e}")
        return jsonify({'error': 'Failed to get credentials', 'details': str(e)}), 500

@credentials_bp.route('/credentials', methods=['PUT'])
@token_required
def update_credentials(current_user):
    """
    Update user's credentials (verification_selfie and/or valid_id)
    Requires Authorization header with Bearer token

    Form data:
        - verification_selfie (file, optional)
        - valid_id (file, optional)
    """
    try:
        # Get database connection
        from app import get_db_connection
        conn = get_db_connection()

        update_data = {}

        # Upload verification selfie if provided
        if 'verification_selfie' in request.files:
            verification_selfie = request.files['verification_selfie']
            print(f"Verification selfie received: {verification_selfie.filename}")
            if verification_selfie and verification_selfie.filename != '' and allowed_file(verification_selfie.filename):
                verification_selfie_path = r2_storage.upload_file(
                    verification_selfie,
                    'verifications/selfies'
                )
                print(f"Verification selfie uploaded to: {verification_selfie_path}")
                update_data['verification_selfie'] = verification_selfie_path
            elif verification_selfie and verification_selfie.filename != '':
                print(f"Verification selfie file type not allowed: {verification_selfie.filename}")
                return jsonify({'error': 'Verification selfie file type not allowed'}), 400

        # Upload valid ID if provided
        if 'valid_id' in request.files:
            valid_id = request.files['valid_id']
            print(f"Valid ID received: {valid_id.filename}")
            if valid_id and valid_id.filename != '' and allowed_file(valid_id.filename):
                valid_id_path = r2_storage.upload_file(valid_id, 'verifications/ids')
                print(f"Valid ID uploaded to: {valid_id_path}")
                update_data['valid_id'] = valid_id_path
            elif valid_id and valid_id.filename != '':
                print(f"Valid ID file type not allowed: {valid_id.filename}")
                return jsonify({'error': 'Valid ID file type not allowed'}), 400

        if not update_data:
            return jsonify({'error': 'No valid files provided'}), 400

        # Update user credentials in database
        success = AuthModel.update_user(conn, current_user['id'], update_data)

        if not success:
            return jsonify({'error': 'Failed to update credentials'}), 500

        # Get updated user
        updated_user = AuthModel.get_user_by_id(conn, current_user['id'])

        # Return only the updated credential URLs
        user_credentials = {}
        if 'verification_selfie' in update_data and updated_user.get('verification_selfie'):
            url = r2_storage.get_file_url(updated_user['verification_selfie'], expiration=604800)
            if url:
                user_credentials['verification_selfie'] = url

        if 'valid_id' in update_data and updated_user.get('valid_id'):
            url = r2_storage.get_file_url(updated_user['valid_id'], expiration=604800)
            if url:
                user_credentials['valid_id'] = url

        return jsonify({
            'message': 'Credentials updated successfully',
            'credentials': user_credentials
        }), 200

    except Exception as e:
        print(f"Update credentials error: {e}")
        return jsonify({'error': 'Failed to update credentials', 'details': str(e)}), 500

@credentials_bp.route('/ids', methods=['GET'])
@token_required
def get_ids(current_user):
    """
    Get user's valid_id only (skip verification_selfie)
    Requires Authorization header with Bearer token

    Returns presigned URL for the valid_id image
    """
    try:
        user_id_data = {}

        # Get valid_id URL if exists (skip verification_selfie)
        if current_user.get('valid_id'):
            url = r2_storage.get_file_url(current_user['valid_id'], expiration=604800)
            if url:
                user_id_data['valid_id'] = url

        return jsonify({
            'id_document': user_id_data
        }), 200

    except Exception as e:
        print(f"Get ID error: {e}")
        return jsonify({'error': 'Failed to get ID', 'details': str(e)}), 500

@credentials_bp.route('/profile-image', methods=['GET'])
@token_required
def get_profile_image(current_user):
    """
    Get user's profile image
    Requires Authorization header with Bearer token

    Returns presigned URL for the profile image
    """
    try:
        profile_data = {}

        # Get profile_image URL if exists
        if current_user.get('profile_image'):
            url = r2_storage.get_file_url(current_user['profile_image'], expiration=604800)
            if url:
                profile_data['profile_image'] = url

        return jsonify({
            'profile': profile_data
        }), 200

    except Exception as e:
        print(f"Get profile image error: {e}")
        return jsonify({'error': 'Failed to get profile image', 'details': str(e)}), 500

@credentials_bp.route('/profile-image', methods=['PUT'])
@token_required
def update_profile_image(current_user):
    """
    Update user's profile image
    Requires Authorization header with Bearer token

    Form data:
        - profile_image (file, required)
    """
    try:
        # Get database connection
        from app import get_db_connection
        conn = get_db_connection()

        # Upload profile image if provided
        if 'profile_image' not in request.files:
            return jsonify({'error': 'No profile image provided'}), 400

        profile_image = request.files['profile_image']
        print(f"Profile image received: {profile_image.filename}")

        if not profile_image or profile_image.filename == '':
            return jsonify({'error': 'No profile image provided'}), 400

        if not allowed_file(profile_image.filename):
            print(f"Profile image file type not allowed: {profile_image.filename}")
            return jsonify({'error': 'Profile image file type not allowed'}), 400

        # Upload to R2 storage
        profile_image_path = r2_storage.upload_file(profile_image, 'profiles')
        print(f"Profile image uploaded to: {profile_image_path}")

        # Update user profile image in database
        success = AuthModel.update_user(conn, current_user['id'], {
            'profile_image': profile_image_path
        })

        if not success:
            return jsonify({'error': 'Failed to update profile image'}), 500

        # Get updated user
        updated_user = AuthModel.get_user_by_id(conn, current_user['id'])

        # Return the updated profile image URL
        profile_data = {}
        if updated_user.get('profile_image'):
            url = r2_storage.get_file_url(updated_user['profile_image'], expiration=604800)
            if url:
                profile_data['profile_image'] = url

        return jsonify({
            'message': 'Profile image updated successfully',
            'profile': profile_data
        }), 200

    except Exception as e:
        print(f"Update profile image error: {e}")
        return jsonify({'error': 'Failed to update profile image', 'details': str(e)}), 500

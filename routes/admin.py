from flask import Blueprint, request, jsonify
from functools import wraps

from models.admin_model import AdminModel
from routes.auth import token_required, process_user_images
from utils.r2_storage import r2_storage

admin_bp = Blueprint('admin', __name__)


def admin_required(f):
    """
    Decorator to protect admin routes
    TODO: Customize this to check for specific admin roles/permissions
    For now, it requires a valid token. You can add additional checks like:
    - Check if user's account_type is 'verified_organization'
    - Check if user's email is in an admin list
    - Add an 'is_admin' field to users table
    """
    @wraps(f)
    @token_required
    def decorated(current_user, *args, **kwargs):
        # Example: Uncomment to restrict to verified organizations only
        # if current_user.get('account_type') != 'verified_organization':
        #     return jsonify({'error': 'Admin access required'}), 403

        # Example: Uncomment to restrict to specific emails
        # admin_emails = ['admin@helplink.com', 'support@helplink.com']
        # if current_user.get('email') not in admin_emails:
        #     return jsonify({'error': 'Admin access required'}), 403

        return f(current_user, *args, **kwargs)

    return decorated


def process_image_urls(items, image_fields):
    """
    Convert image paths to full URLs using R2 storage presigned URLs

    Args:
        items: List of dictionaries containing image paths
        image_fields: List of field names containing image paths

    Returns:
        List with image paths converted to URLs
    """
    if not items:
        return items

    for item in items:
        for field in image_fields:
            if field in item and item[field]:
                url = r2_storage.get_file_url(item[field], expiration=604800)
                if url:
                    item[field] = url

    return items


# ==================== USER MANAGEMENT ====================

@admin_bp.route('/users', methods=['GET'])
@admin_required
def get_users(current_user):
    """
    Get all users with optional filtering

    Query parameters:
        - limit (optional, default: 50)
        - offset (optional, default: 0)
        - account_type (optional): Filter by account type
        - badge (optional): Filter by badge status
    """
    try:
        limit = int(request.args.get('limit', 50))
        offset = int(request.args.get('offset', 0))
        account_type = request.args.get('account_type')
        badge = request.args.get('badge')

        # Get database connection
        from app import get_db_connection
        conn = get_db_connection()

        result = AdminModel.get_all_users(conn, limit, offset, account_type, badge)

        if result is None:
            return jsonify({'error': 'Failed to fetch users'}), 500

        # Process user images
        image_fields = ['profile_image', 'verification_selfie', 'valid_id']
        result['users'] = process_image_urls(result['users'], image_fields)

        return jsonify(result), 200

    except ValueError:
        return jsonify({'error': 'Invalid limit or offset parameter'}), 400
    except Exception as e:
        print(f"Get users error: {e}")
        return jsonify({'error': 'Failed to fetch users', 'details': str(e)}), 500


@admin_bp.route('/users/verification-requests', methods=['GET'])
@admin_required
def get_verification_requests(current_user):
    """
    Get users pending verification

    Query parameters:
        - limit (optional, default: 50)
        - offset (optional, default: 0)
    """
    try:
        limit = int(request.args.get('limit', 50))
        offset = int(request.args.get('offset', 0))

        # Get database connection
        from app import get_db_connection
        conn = get_db_connection()

        result = AdminModel.get_verification_requests(conn, limit, offset)

        if result is None:
            return jsonify({'error': 'Failed to fetch verification requests'}), 500

        # Process user images
        image_fields = ['profile_image', 'verification_selfie', 'valid_id']
        result['users'] = process_image_urls(result['users'], image_fields)

        return jsonify(result), 200

    except ValueError:
        return jsonify({'error': 'Invalid limit or offset parameter'}), 400
    except Exception as e:
        print(f"Get verification requests error: {e}")
        return jsonify({'error': 'Failed to fetch verification requests', 'details': str(e)}), 500


@admin_bp.route('/users/<int:user_id>/badge', methods=['PUT'])
@admin_required
def update_user_badge(current_user, user_id):
    """
    Update user's verification badge

    JSON body:
        - badge (required): 'verified' or 'under_review'
    """
    try:
        data = request.get_json()

        if not data:
            return jsonify({'error': 'No data provided'}), 400

        badge = data.get('badge')

        if badge not in ['verified', 'under_review']:
            return jsonify({'error': 'Invalid badge value. Must be "verified" or "under_review"'}), 400

        # Get database connection
        from app import get_db_connection
        conn = get_db_connection()

        success = AdminModel.update_user_badge(conn, user_id, badge)

        if not success:
            return jsonify({'error': 'Failed to update user badge'}), 500

        return jsonify({
            'message': 'User badge updated successfully',
            'user_id': user_id,
            'badge': badge
        }), 200

    except Exception as e:
        print(f"Update badge error: {e}")
        return jsonify({'error': 'Failed to update badge', 'details': str(e)}), 500


@admin_bp.route('/users/<int:user_id>/account-type', methods=['PUT'])
@admin_required
def update_user_account_type(current_user, user_id):
    """
    Update user's account type

    JSON body:
        - account_type (required): 'beneficiary', 'donor', 'volunteer', or 'verified_organization'
    """
    try:
        data = request.get_json()

        if not data:
            return jsonify({'error': 'No data provided'}), 400

        account_type = data.get('account_type')

        valid_types = ['beneficiary', 'donor', 'volunteer', 'verified_organization']
        if account_type not in valid_types:
            return jsonify({'error': f'Invalid account type. Must be one of: {", ".join(valid_types)}'}), 400

        # Get database connection
        from app import get_db_connection
        conn = get_db_connection()

        success = AdminModel.update_user_account_type(conn, user_id, account_type)

        if not success:
            return jsonify({'error': 'Failed to update account type'}), 500

        return jsonify({
            'message': 'Account type updated successfully',
            'user_id': user_id,
            'account_type': account_type
        }), 200

    except Exception as e:
        print(f"Update account type error: {e}")
        return jsonify({'error': 'Failed to update account type', 'details': str(e)}), 500


# ==================== POST MANAGEMENT ====================

@admin_bp.route('/posts', methods=['GET'])
@admin_required
def get_posts(current_user):
    """
    Get all posts with optional filtering

    Query parameters:
        - limit (optional, default: 50)
        - offset (optional, default: 0)
        - post_type (optional): Filter by post type ('donation' or 'request')
        - status (optional): Filter by status ('active', 'closed', 'pending')
    """
    try:
        limit = int(request.args.get('limit', 50))
        offset = int(request.args.get('offset', 0))
        post_type = request.args.get('post_type')
        status = request.args.get('status')

        # Get database connection
        from app import get_db_connection
        conn = get_db_connection()

        result = AdminModel.get_all_posts(conn, limit, offset, post_type, status)

        if result is None:
            return jsonify({'error': 'Failed to fetch posts'}), 500

        # Process user profile images
        for post in result['posts']:
            if 'profile_image' in post and post['profile_image']:
                url = r2_storage.get_file_url(post['profile_image'], expiration=604800)
                if url:
                    post['profile_image'] = url

        return jsonify(result), 200

    except ValueError:
        return jsonify({'error': 'Invalid limit or offset parameter'}), 400
    except Exception as e:
        print(f"Get posts error: {e}")
        return jsonify({'error': 'Failed to fetch posts', 'details': str(e)}), 500


@admin_bp.route('/posts/<int:post_id>/status', methods=['PUT'])
@admin_required
def update_post_status(current_user, post_id):
    """
    Update post status

    JSON body:
        - status (required): 'active', 'closed', or 'pending'
    """
    try:
        data = request.get_json()

        if not data:
            return jsonify({'error': 'No data provided'}), 400

        status = data.get('status')

        if status not in ['active', 'closed', 'pending']:
            return jsonify({'error': 'Invalid status. Must be "active", "closed", or "pending"'}), 400

        # Get database connection
        from app import get_db_connection
        conn = get_db_connection()

        success = AdminModel.update_post_status(conn, post_id, status)

        if not success:
            return jsonify({'error': 'Failed to update post status'}), 500

        return jsonify({
            'message': 'Post status updated successfully',
            'post_id': post_id,
            'status': status
        }), 200

    except Exception as e:
        print(f"Update post status error: {e}")
        return jsonify({'error': 'Failed to update post status', 'details': str(e)}), 500


# ==================== COMMENT MODERATION ====================

@admin_bp.route('/comments', methods=['GET'])
@admin_required
def get_comments(current_user):
    """
    Get all comments with optional filtering

    Query parameters:
        - limit (optional, default: 50)
        - offset (optional, default: 0)
        - status (optional): Filter by status ('visible', 'hidden', 'deleted')
    """
    try:
        limit = int(request.args.get('limit', 50))
        offset = int(request.args.get('offset', 0))
        status = request.args.get('status')

        # Get database connection
        from app import get_db_connection
        conn = get_db_connection()

        result = AdminModel.get_all_comments(conn, limit, offset, status)

        if result is None:
            return jsonify({'error': 'Failed to fetch comments'}), 500

        return jsonify(result), 200

    except ValueError:
        return jsonify({'error': 'Invalid limit or offset parameter'}), 400
    except Exception as e:
        print(f"Get comments error: {e}")
        return jsonify({'error': 'Failed to fetch comments', 'details': str(e)}), 500


@admin_bp.route('/comments/<int:comment_id>/status', methods=['PUT'])
@admin_required
def update_comment_status(current_user, comment_id):
    """
    Update comment status (for moderation)

    JSON body:
        - status (required): 'visible', 'hidden', or 'deleted'
    """
    try:
        data = request.get_json()

        if not data:
            return jsonify({'error': 'No data provided'}), 400

        status = data.get('status')

        if status not in ['visible', 'hidden', 'deleted']:
            return jsonify({'error': 'Invalid status. Must be "visible", "hidden", or "deleted"'}), 400

        # Get database connection
        from app import get_db_connection
        conn = get_db_connection()

        success = AdminModel.update_comment_status(conn, comment_id, status)

        if not success:
            return jsonify({'error': 'Failed to update comment status'}), 500

        return jsonify({
            'message': 'Comment status updated successfully',
            'comment_id': comment_id,
            'status': status
        }), 200

    except Exception as e:
        print(f"Update comment status error: {e}")
        return jsonify({'error': 'Failed to update comment status', 'details': str(e)}), 500


# ==================== DONATION MANAGEMENT ====================

@admin_bp.route('/donations', methods=['GET'])
@admin_required
def get_donations(current_user):
    """
    Get all donations with optional filtering

    Query parameters:
        - limit (optional, default: 50)
        - offset (optional, default: 0)
        - verification_status (optional): Filter by verification status ('pending', 'ongoing', 'fulfilled')
    """
    try:
        limit = int(request.args.get('limit', 50))
        offset = int(request.args.get('offset', 0))
        verification_status = request.args.get('verification_status')

        # Get database connection
        from app import get_db_connection
        conn = get_db_connection()

        result = AdminModel.get_all_donations(conn, limit, offset, verification_status)

        if result is None:
            return jsonify({'error': 'Failed to fetch donations'}), 500

        # Process proof images
        for donation in result['donations']:
            if 'proofs' in donation:
                for proof in donation['proofs']:
                    if 'image_url' in proof and proof['image_url']:
                        url = r2_storage.get_file_url(proof['image_url'], expiration=604800)
                        if url:
                            proof['image_url'] = url

        return jsonify(result), 200

    except ValueError:
        return jsonify({'error': 'Invalid limit or offset parameter'}), 400
    except Exception as e:
        print(f"Get donations error: {e}")
        return jsonify({'error': 'Failed to fetch donations', 'details': str(e)}), 500


@admin_bp.route('/donations/<int:donation_id>/status', methods=['PUT'])
@admin_required
def update_donation_status(current_user, donation_id):
    """
    Update donation verification status

    JSON body:
        - verification_status (required): 'pending', 'ongoing', or 'fulfilled'
    """
    try:
        data = request.get_json()

        if not data:
            return jsonify({'error': 'No data provided'}), 400

        verification_status = data.get('verification_status')

        if verification_status not in ['pending', 'ongoing', 'fulfilled']:
            return jsonify({'error': 'Invalid status. Must be "pending", "ongoing", or "fulfilled"'}), 400

        # Get database connection
        from app import get_db_connection
        conn = get_db_connection()

        success = AdminModel.update_donation_status(conn, donation_id, verification_status)

        if not success:
            return jsonify({'error': 'Failed to update donation status'}), 500

        return jsonify({
            'message': 'Donation status updated successfully',
            'donation_id': donation_id,
            'verification_status': verification_status
        }), 200

    except Exception as e:
        print(f"Update donation status error: {e}")
        return jsonify({'error': 'Failed to update donation status', 'details': str(e)}), 500


# ==================== SUPPORTER MANAGEMENT ====================

@admin_bp.route('/supporters', methods=['GET'])
@admin_required
def get_supporters(current_user):
    """
    Get all supporters

    Query parameters:
        - limit (optional, default: 50)
        - offset (optional, default: 0)
    """
    try:
        limit = int(request.args.get('limit', 50))
        offset = int(request.args.get('offset', 0))

        # Get database connection
        from app import get_db_connection
        conn = get_db_connection()

        result = AdminModel.get_all_supporters(conn, limit, offset)

        if result is None:
            return jsonify({'error': 'Failed to fetch supporters'}), 500

        # Process proof images
        for supporter in result['supporters']:
            if 'proofs' in supporter:
                for proof in supporter['proofs']:
                    if 'image_url' in proof and proof['image_url']:
                        url = r2_storage.get_file_url(proof['image_url'], expiration=604800)
                        if url:
                            proof['image_url'] = url

        return jsonify(result), 200

    except ValueError:
        return jsonify({'error': 'Invalid limit or offset parameter'}), 400
    except Exception as e:
        print(f"Get supporters error: {e}")
        return jsonify({'error': 'Failed to fetch supporters', 'details': str(e)}), 500


# ==================== STATISTICS & ANALYTICS ====================

@admin_bp.route('/statistics', methods=['GET'])
@admin_required
def get_statistics(current_user):
    """
    Get platform statistics and analytics
    """
    try:
        # Get database connection
        from app import get_db_connection
        conn = get_db_connection()

        stats = AdminModel.get_statistics(conn)

        if stats is None:
            return jsonify({'error': 'Failed to fetch statistics'}), 500

        return jsonify(stats), 200

    except Exception as e:
        print(f"Get statistics error: {e}")
        return jsonify({'error': 'Failed to fetch statistics', 'details': str(e)}), 500


@admin_bp.route('/activity', methods=['GET'])
@admin_required
def get_recent_activity(current_user):
    """
    Get recent platform activity

    Query parameters:
        - limit (optional, default: 20)
    """
    try:
        limit = int(request.args.get('limit', 20))

        # Get database connection
        from app import get_db_connection
        conn = get_db_connection()

        activities = AdminModel.get_recent_activity(conn, limit)

        if activities is None:
            return jsonify({'error': 'Failed to fetch recent activity'}), 500

        return jsonify({
            'activities': activities,
            'count': len(activities)
        }), 200

    except ValueError:
        return jsonify({'error': 'Invalid limit parameter'}), 400
    except Exception as e:
        print(f"Get activity error: {e}")
        return jsonify({'error': 'Failed to fetch activity', 'details': str(e)}), 500


# ==================== DASHBOARD ====================

@admin_bp.route('/dashboard', methods=['GET'])
@admin_required
def get_dashboard(current_user):
    """
    Get comprehensive dashboard data including statistics and recent activity
    """
    try:
        # Get database connection
        from app import get_db_connection
        conn = get_db_connection()

        # Get statistics
        stats = AdminModel.get_statistics(conn)
        if stats is None:
            return jsonify({'error': 'Failed to fetch statistics'}), 500

        # Get recent activity
        activities = AdminModel.get_recent_activity(conn, limit=10)
        if activities is None:
            return jsonify({'error': 'Failed to fetch activity'}), 500

        # Get pending verification count
        verification_requests = AdminModel.get_verification_requests(conn, limit=1, offset=0)
        pending_verifications = verification_requests['total'] if verification_requests else 0

        # Get pending donations count
        pending_donations_result = AdminModel.get_all_donations(
            conn, limit=1, offset=0, verification_status='pending'
        )
        pending_donations = pending_donations_result['total'] if pending_donations_result else 0

        return jsonify({
            'statistics': stats,
            'recent_activity': activities,
            'pending_verifications': pending_verifications,
            'pending_donations': pending_donations
        }), 200

    except Exception as e:
        print(f"Get dashboard error: {e}")
        return jsonify({'error': 'Failed to fetch dashboard data', 'details': str(e)}), 500

from flask import Blueprint, request, jsonify

from models.post_model import PostModel
from routes.auth import token_required
from utils.r2_storage import r2_storage

post_bp = Blueprint('post', __name__)

# Allowed file extensions
ALLOWED_IMAGE_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}
ALLOWED_VIDEO_EXTENSIONS = {'mp4', 'mov', 'avi', 'webm'}


def allowed_file(filename, allowed_extensions):
    """Check if file extension is allowed"""
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in allowed_extensions


def process_media_urls(media_paths):
    """
    Convert media paths to full URLs using R2 storage presigned URLs

    Args:
        media_paths: List of media file paths

    Returns:
        List of presigned URLs
    """
    if not media_paths:
        return []

    urls = []
    for path in media_paths:
        # Generate presigned URL (valid for 7 days)
        url = r2_storage.get_file_url(path, expiration=604800)
        if url:
            urls.append(url)
    return urls


def process_post_data(post):
    """
    Process post data to convert media paths to URLs

    Args:
        post: Dictionary containing post information

    Returns:
        Dictionary with media paths converted to URLs
    """
    if not post:
        return post

    # Convert photo paths to URLs
    if 'photos' in post:
        post['photos'] = process_media_urls(post['photos'])

    # Convert video paths to URLs
    if 'videos' in post:
        post['videos'] = process_media_urls(post['videos'])

    # Convert profile image to URL
    if 'profile_image' in post and post['profile_image']:
        url = r2_storage.get_file_url(post['profile_image'], expiration=604800)
        if url:
            post['profile_image'] = url

    return post


def process_user_profile_images(items):
    """
    Process profile images in a list of items (reactions, donators, supporters, etc.)

    Args:
        items: List of dictionaries containing user profile_image

    Returns:
        List with profile images converted to URLs
    """
    if not items:
        return items

    for item in items:
        if 'profile_image' in item and item['profile_image']:
            url = r2_storage.get_file_url(item['profile_image'], expiration=604800)
            if url:
                item['profile_image'] = url

    return items


def get_expanded_post_data(conn, post, current_user_id):
    """
    Get expanded data for a post including reactions, donators, supporters, and comments

    Args:
        conn: Database connection
        post: Post dictionary
        current_user_id: Current user's ID

    Returns:
        Post dictionary with expanded data
    """
    # Get reactions with user details
    reactions = PostModel.get_post_reactions(conn, post['id'])
    post['reactions'] = process_user_profile_images(reactions)

    # Get donators with user details
    donators = PostModel.get_post_donators(conn, post['id'])
    post['donators'] = process_user_profile_images(donators)

    # Get supporters with user details
    supporters = PostModel.get_post_supporters(conn, post['id'])
    post['supporters'] = process_user_profile_images(supporters)

    # Get comments with user details (limit to 10 recent comments)
    comments = PostModel.get_comments(conn, post['id'], 'visible', limit=10, offset=0)

    # Process profile images for comments and replies
    for comment in comments:
        if 'profile_image' in comment and comment['profile_image']:
            url = r2_storage.get_file_url(comment['profile_image'], expiration=604800)
            if url:
                comment['profile_image'] = url

        # Process replies
        if 'replies' in comment:
            for reply in comment['replies']:
                if 'profile_image' in reply and reply['profile_image']:
                    url = r2_storage.get_file_url(reply['profile_image'], expiration=604800)
                    if url:
                        reply['profile_image'] = url

    post['comments'] = comments

    return post


@post_bp.route('', methods=['POST'])
@token_required
def create_post(current_user):
    """
    Create a new post with optional media uploads

    Form data:
        - post_type (required): 'donation' or 'request'
        - title (required)
        - description (optional)
        - address (optional)
        - latitude (optional)
        - longitude (optional)
        - photos[] (files, optional): Multiple photo uploads
        - videos[] (files, optional): Multiple video uploads
    """
    try:
        # Get form data
        post_type = request.form.get('post_type')
        title = request.form.get('title')
        description = request.form.get('description')
        address = request.form.get('address')
        latitude = request.form.get('latitude')
        longitude = request.form.get('longitude')

        # Validate required fields
        if not all([post_type, title]):
            return jsonify({
                'error': 'Missing required fields',
                'required': ['post_type', 'title']
            }), 400

        # Validate post_type
        if post_type not in ['donation', 'request']:
            return jsonify({
                'error': 'Invalid post_type',
                'allowed_values': ['donation', 'request']
            }), 400

        # Get database connection
        from app import get_db_connection
        conn = get_db_connection()

        # Handle photo uploads
        photo_paths = []
        if 'photos' in request.files:
            photos = request.files.getlist('photos')
            for photo in photos:
                if photo and photo.filename != '' and allowed_file(photo.filename, ALLOWED_IMAGE_EXTENSIONS):
                    photo_path = r2_storage.upload_file(photo, 'posts/photos')
                    if photo_path:
                        photo_paths.append(photo_path)
                        print(f"Photo uploaded to: {photo_path}")

        # Handle video uploads
        video_paths = []
        if 'videos' in request.files:
            videos = request.files.getlist('videos')
            for video in videos:
                if video and video.filename != '' and allowed_file(video.filename, ALLOWED_VIDEO_EXTENSIONS):
                    video_path = r2_storage.upload_file(video, 'posts/videos')
                    if video_path:
                        video_paths.append(video_path)
                        print(f"Video uploaded to: {video_path}")

        # Prepare post data
        post_data = {
            'user_id': current_user['id'],
            'post_type': post_type,
            'title': title,
            'description': description,
            'address': address,
            'latitude': float(latitude) if latitude else None,
            'longitude': float(longitude) if longitude else None,
            'status': 'active',
            'photos': photo_paths,
            'videos': video_paths
        }

        # Create post
        post_id = PostModel.create_post(conn, post_data)

        if not post_id:
            return jsonify({'error': 'Failed to create post'}), 500

        # Get created post
        post = PostModel.get_post_by_id(conn, post_id, current_user['id'])

        # Process post media to return full URLs
        post = process_post_data(post)

        return jsonify({
            'message': 'Post created successfully',
            'post': post
        }), 201

    except Exception as e:
        print(f"Create post error: {e}")
        return jsonify({'error': 'Failed to create post', 'details': str(e)}), 500


@post_bp.route('', methods=['GET'])
@token_required
def get_posts(current_user):
    """
    Get all posts with optional filters

    Query parameters:
        - user_id (optional): Filter by user
        - post_type (optional): Filter by type ('donation' or 'request')
        - status (optional): Filter by status ('active', 'closed', 'pending')
        - limit (optional, default: 20): Number of posts to return
        - offset (optional, default: 0): Offset for pagination
    """
    try:
        # Get query parameters
        user_id = request.args.get('user_id', type=int)
        post_type = request.args.get('post_type')
        status = request.args.get('status')
        limit = request.args.get('limit', default=20, type=int)
        offset = request.args.get('offset', default=0, type=int)

        # Build filters
        filters = {}
        if user_id:
            filters['user_id'] = user_id
        if post_type:
            filters['post_type'] = post_type
        if status:
            filters['status'] = status

        # Get database connection
        from app import get_db_connection
        conn = get_db_connection()

        # Get posts
        posts = PostModel.get_posts(conn, filters, current_user['id'], limit, offset)

        # Process all posts to convert media paths to URLs
        processed_posts = [process_post_data(post) for post in posts]

        return jsonify({
            'posts': processed_posts,
            'count': len(processed_posts),
            'limit': limit,
            'offset': offset
        }), 200

    except Exception as e:
        print(f"Get posts error: {e}")
        return jsonify({'error': 'Failed to get posts', 'details': str(e)}), 500


@post_bp.route('/donations', methods=['GET'])
@token_required
def get_donation_posts(current_user):
    """
    Get all donation posts with optional filters and expanded data

    Query parameters:
        - user_id (optional): Filter by user
        - status (optional): Filter by status ('active', 'closed', 'pending')
        - limit (optional, default: 20): Number of posts to return
        - offset (optional, default: 0): Offset for pagination

    Returns posts with:
        - Post details (title, description, address, etc.)
        - Photos and videos (presigned URLs)
        - Reactions with user details
        - Donators with user details
        - Supporters with user details
        - Comments with user details (10 recent)
    """
    try:
        # Get query parameters
        user_id = request.args.get('user_id', type=int)
        status = request.args.get('status')
        limit = request.args.get('limit', default=20, type=int)
        offset = request.args.get('offset', default=0, type=int)

        # Build filters with post_type set to 'donation'
        filters = {'post_type': 'donation'}
        if user_id:
            filters['user_id'] = user_id
        if status:
            filters['status'] = status

        # Get database connection
        from app import get_db_connection
        conn = get_db_connection()

        # Get posts
        posts = PostModel.get_posts(conn, filters, current_user['id'], limit, offset)

        # Process all posts to convert media paths to URLs and add expanded data
        processed_posts = []
        for post in posts:
            # Process basic post data (photos, videos, profile_image)
            post = process_post_data(post)

            # Add expanded data (reactions, donators, supporters, comments)
            post = get_expanded_post_data(conn, post, current_user['id'])

            processed_posts.append(post)

        return jsonify({
            'posts': processed_posts,
            'count': len(processed_posts),
            'post_type': 'donation',
            'limit': limit,
            'offset': offset
        }), 200

    except Exception as e:
        print(f"Get donation posts error: {e}")
        return jsonify({'error': 'Failed to get donation posts', 'details': str(e)}), 500


@post_bp.route('/requests', methods=['GET'])
@token_required
def get_request_posts(current_user):
    """
    Get all request posts with optional filters and expanded data

    Query parameters:
        - user_id (optional): Filter by user
        - status (optional): Filter by status ('active', 'closed', 'pending')
        - limit (optional, default: 20): Number of posts to return
        - offset (optional, default: 0): Offset for pagination

    Returns posts with:
        - Post details (title, description, address, etc.)
        - Photos and videos (presigned URLs)
        - Reactions with user details
        - Donators with user details
        - Supporters with user details
        - Comments with user details (10 recent)
    """
    try:
        # Get query parameters
        user_id = request.args.get('user_id', type=int)
        status = request.args.get('status')
        limit = request.args.get('limit', default=20, type=int)
        offset = request.args.get('offset', default=0, type=int)

        # Build filters with post_type set to 'request'
        filters = {'post_type': 'request'}
        if user_id:
            filters['user_id'] = user_id
        if status:
            filters['status'] = status

        # Get database connection
        from app import get_db_connection
        conn = get_db_connection()

        # Get posts
        posts = PostModel.get_posts(conn, filters, current_user['id'], limit, offset)

        # Process all posts to convert media paths to URLs and add expanded data
        processed_posts = []
        for post in posts:
            # Process basic post data (photos, videos, profile_image)
            post = process_post_data(post)

            # Add expanded data (reactions, donators, supporters, comments)
            post = get_expanded_post_data(conn, post, current_user['id'])

            processed_posts.append(post)

        return jsonify({
            'posts': processed_posts,
            'count': len(processed_posts),
            'post_type': 'request',
            'limit': limit,
            'offset': offset
        }), 200

    except Exception as e:
        print(f"Get request posts error: {e}")
        return jsonify({'error': 'Failed to get request posts', 'details': str(e)}), 500


@post_bp.route('/<int:post_id>', methods=['GET'])
@token_required
def get_post(current_user, post_id):
    """
    Get a single post by ID

    Path parameters:
        - post_id: Post ID
    """
    try:
        # Get database connection
        from app import get_db_connection
        conn = get_db_connection()

        # Get post
        post = PostModel.get_post_by_id(conn, post_id, current_user['id'])

        if not post:
            return jsonify({'error': 'Post not found'}), 404

        # Process post media to return full URLs
        post = process_post_data(post)

        return jsonify({
            'post': post
        }), 200

    except Exception as e:
        print(f"Get post error: {e}")
        return jsonify({'error': 'Failed to get post', 'details': str(e)}), 500


@post_bp.route('/<int:post_id>', methods=['PUT'])
@token_required
def update_post(current_user, post_id):
    """
    Update a post (only by owner)

    Path parameters:
        - post_id: Post ID

    JSON body:
        - title (optional)
        - description (optional)
        - address (optional)
        - latitude (optional)
        - longitude (optional)
    """
    try:
        data = request.get_json()

        if not data:
            return jsonify({'error': 'No data provided'}), 400

        # Get database connection
        from app import get_db_connection
        conn = get_db_connection()

        # Prepare update data
        update_data = {}
        allowed_fields = ['title', 'description', 'address', 'latitude', 'longitude']

        for field in allowed_fields:
            if field in data:
                # Convert coordinates to float if provided
                if field in ['latitude', 'longitude'] and data[field] is not None:
                    try:
                        update_data[field] = float(data[field])
                    except (ValueError, TypeError):
                        return jsonify({'error': f'Invalid value for {field}'}), 400
                else:
                    update_data[field] = data[field]

        if not update_data:
            return jsonify({'error': 'No valid fields to update'}), 400

        # Update post
        success = PostModel.update_post(conn, post_id, current_user['id'], update_data)

        if not success:
            return jsonify({'error': 'Failed to update post or unauthorized'}), 403

        # Get updated post
        post = PostModel.get_post_by_id(conn, post_id, current_user['id'])

        # Process post media to return full URLs
        post = process_post_data(post)

        return jsonify({
            'message': 'Post updated successfully',
            'post': post
        }), 200

    except Exception as e:
        print(f"Update post error: {e}")
        return jsonify({'error': 'Failed to update post', 'details': str(e)}), 500


@post_bp.route('/<int:post_id>/close', methods=['PUT'])
@token_required
def close_post(current_user, post_id):
    """
    Close a post (update status to 'closed')

    Path parameters:
        - post_id: Post ID
    """
    try:
        # Get database connection
        from app import get_db_connection
        conn = get_db_connection()

        # Close post
        success = PostModel.close_post(conn, post_id, current_user['id'])

        if not success:
            return jsonify({'error': 'Failed to close post or unauthorized'}), 403

        # Get updated post
        post = PostModel.get_post_by_id(conn, post_id, current_user['id'])

        # Process post media to return full URLs
        post = process_post_data(post)

        return jsonify({
            'message': 'Post closed successfully',
            'post': post
        }), 200

    except Exception as e:
        print(f"Close post error: {e}")
        return jsonify({'error': 'Failed to close post', 'details': str(e)}), 500


@post_bp.route('/<int:post_id>/reaction', methods=['POST'])
@token_required
def add_reaction(current_user, post_id):
    """
    Add or update a reaction to a post

    Path parameters:
        - post_id: Post ID

    JSON body:
        - reaction_type (required): 'like', 'love', 'care', 'support'
    """
    try:
        data = request.get_json()

        if not data:
            return jsonify({'error': 'No data provided'}), 400

        reaction_type = data.get('reaction_type', 'like')

        # Validate reaction type
        valid_reactions = ['like', 'love', 'care', 'support']
        if reaction_type not in valid_reactions:
            return jsonify({
                'error': 'Invalid reaction_type',
                'allowed_values': valid_reactions
            }), 400

        # Get database connection
        from app import get_db_connection
        conn = get_db_connection()

        # Add reaction
        success = PostModel.add_reaction(conn, post_id, current_user['id'], reaction_type)

        if not success:
            return jsonify({'error': 'Failed to add reaction'}), 500

        # Get updated post
        post = PostModel.get_post_by_id(conn, post_id, current_user['id'])

        # Process post media to return full URLs
        post = process_post_data(post)

        return jsonify({
            'message': 'Reaction added successfully',
            'post': post
        }), 200

    except Exception as e:
        print(f"Add reaction error: {e}")
        return jsonify({'error': 'Failed to add reaction', 'details': str(e)}), 500


@post_bp.route('/<int:post_id>/reaction', methods=['DELETE'])
@token_required
def remove_reaction(current_user, post_id):
    """
    Remove a reaction from a post

    Path parameters:
        - post_id: Post ID
    """
    try:
        # Get database connection
        from app import get_db_connection
        conn = get_db_connection()

        # Remove reaction
        success = PostModel.remove_reaction(conn, post_id, current_user['id'])

        if not success:
            return jsonify({'error': 'Failed to remove reaction'}), 500

        # Get updated post
        post = PostModel.get_post_by_id(conn, post_id, current_user['id'])

        # Process post media to return full URLs
        post = process_post_data(post)

        return jsonify({
            'message': 'Reaction removed successfully',
            'post': post
        }), 200

    except Exception as e:
        print(f"Remove reaction error: {e}")
        return jsonify({'error': 'Failed to remove reaction', 'details': str(e)}), 500


@post_bp.route('/<int:post_id>/donate', methods=['POST'])
@token_required
def add_donation(current_user, post_id):
    """
    Add a donation to a post

    Path parameters:
        - post_id: Post ID

    JSON body:
        - amount (required): Donation amount
        - message (optional): Message from donator
    """
    try:
        data = request.get_json()

        if not data:
            return jsonify({'error': 'No data provided'}), 400

        amount = data.get('amount')
        message = data.get('message')

        # Validate required fields
        if amount is None:
            return jsonify({
                'error': 'Missing required fields',
                'required': ['amount']
            }), 400

        # Validate amount
        try:
            amount = float(amount)
            if amount <= 0:
                return jsonify({'error': 'Amount must be greater than 0'}), 400
        except (ValueError, TypeError):
            return jsonify({'error': 'Invalid amount'}), 400

        # Get database connection
        from app import get_db_connection
        conn = get_db_connection()

        # Add donator
        donator_id = PostModel.add_donator(conn, post_id, current_user['id'], amount, message)

        if not donator_id:
            return jsonify({'error': 'Failed to add donation'}), 500

        return jsonify({
            'message': 'Donation added successfully',
            'donator_id': donator_id
        }), 201

    except Exception as e:
        print(f"Add donation error: {e}")
        return jsonify({'error': 'Failed to add donation', 'details': str(e)}), 500


@post_bp.route('/<int:post_id>/support', methods=['POST'])
@token_required
def add_support(current_user, post_id):
    """
    Add support to a post

    Path parameters:
        - post_id: Post ID

    JSON body:
        - support_type (optional, default: 'share'): 'share', 'volunteer', 'advocate', 'other'
        - message (optional): Message from supporter
    """
    try:
        data = request.get_json()

        support_type = data.get('support_type', 'share') if data else 'share'
        message = data.get('message') if data else None

        # Validate support type
        valid_support_types = ['share', 'volunteer', 'advocate', 'other']
        if support_type not in valid_support_types:
            return jsonify({
                'error': 'Invalid support_type',
                'allowed_values': valid_support_types
            }), 400

        # Get database connection
        from app import get_db_connection
        conn = get_db_connection()

        # Add supporter
        supporter_id = PostModel.add_supporter(conn, post_id, current_user['id'], support_type, message)

        if not supporter_id:
            return jsonify({'error': 'Failed to add support'}), 500

        return jsonify({
            'message': 'Support added successfully',
            'supporter_id': supporter_id
        }), 201

    except Exception as e:
        print(f"Add support error: {e}")
        return jsonify({'error': 'Failed to add support', 'details': str(e)}), 500


@post_bp.route('/<int:post_id>/comments', methods=['POST'])
@token_required
def create_comment(current_user, post_id):
    """
    Create a comment on a post

    Path parameters:
        - post_id: Post ID

    JSON body:
        - content (required): Comment content
        - parent_id (optional): Parent comment ID for replies
    """
    try:
        data = request.get_json()

        if not data:
            return jsonify({'error': 'No data provided'}), 400

        content = data.get('content')
        parent_id = data.get('parent_id')

        # Validate required fields
        if not content:
            return jsonify({
                'error': 'Missing required fields',
                'required': ['content']
            }), 400

        # Validate content length
        if len(content.strip()) == 0:
            return jsonify({'error': 'Comment content cannot be empty'}), 400

        # Get database connection
        from app import get_db_connection
        conn = get_db_connection()

        # Verify post exists
        post = PostModel.get_post_by_id(conn, post_id, current_user['id'])
        if not post:
            return jsonify({'error': 'Post not found'}), 404

        # If parent_id is provided, verify parent comment exists
        if parent_id:
            parent_comment = PostModel.get_comment_by_id(conn, parent_id)
            if not parent_comment:
                return jsonify({'error': 'Parent comment not found'}), 404
            if parent_comment['post_id'] != post_id:
                return jsonify({'error': 'Parent comment does not belong to this post'}), 400

        # Create comment
        comment_id = PostModel.create_comment(conn, post_id, current_user['id'], content, parent_id)

        if not comment_id:
            return jsonify({'error': 'Failed to create comment'}), 500

        # Get created comment
        comment = PostModel.get_comment_by_id(conn, comment_id)

        # Process profile image
        if comment and 'profile_image' in comment and comment['profile_image']:
            url = r2_storage.get_file_url(comment['profile_image'], expiration=604800)
            if url:
                comment['profile_image'] = url

        return jsonify({
            'message': 'Comment created successfully',
            'comment': comment
        }), 201

    except Exception as e:
        print(f"Create comment error: {e}")
        return jsonify({'error': 'Failed to create comment', 'details': str(e)}), 500


@post_bp.route('/<int:post_id>/comments', methods=['GET'])
@token_required
def get_comments(current_user, post_id):
    """
    Get comments for a post

    Path parameters:
        - post_id: Post ID

    Query parameters:
        - limit (optional, default: 50): Number of comments to return
        - offset (optional, default: 0): Offset for pagination
    """
    try:
        # Get query parameters
        limit = request.args.get('limit', default=50, type=int)
        offset = request.args.get('offset', default=0, type=int)

        # Get database connection
        from app import get_db_connection
        conn = get_db_connection()

        # Verify post exists
        post = PostModel.get_post_by_id(conn, post_id, current_user['id'])
        if not post:
            return jsonify({'error': 'Post not found'}), 404

        # Get comments
        comments = PostModel.get_comments(conn, post_id, 'visible', limit, offset)

        # Process profile images for comments and replies
        for comment in comments:
            if 'profile_image' in comment and comment['profile_image']:
                url = r2_storage.get_file_url(comment['profile_image'], expiration=604800)
                if url:
                    comment['profile_image'] = url

            # Process replies
            if 'replies' in comment:
                for reply in comment['replies']:
                    if 'profile_image' in reply and reply['profile_image']:
                        url = r2_storage.get_file_url(reply['profile_image'], expiration=604800)
                        if url:
                            reply['profile_image'] = url

        return jsonify({
            'comments': comments,
            'count': len(comments),
            'limit': limit,
            'offset': offset
        }), 200

    except Exception as e:
        print(f"Get comments error: {e}")
        return jsonify({'error': 'Failed to get comments', 'details': str(e)}), 500


@post_bp.route('/comments/<int:comment_id>', methods=['PUT'])
@token_required
def update_comment(current_user, comment_id):
    """
    Update a comment (only by owner)

    Path parameters:
        - comment_id: Comment ID

    JSON body:
        - content (required): New comment content
    """
    try:
        data = request.get_json()

        if not data:
            return jsonify({'error': 'No data provided'}), 400

        content = data.get('content')

        # Validate required fields
        if not content:
            return jsonify({
                'error': 'Missing required fields',
                'required': ['content']
            }), 400

        # Validate content length
        if len(content.strip()) == 0:
            return jsonify({'error': 'Comment content cannot be empty'}), 400

        # Get database connection
        from app import get_db_connection
        conn = get_db_connection()

        # Update comment
        success = PostModel.update_comment(conn, comment_id, current_user['id'], content)

        if not success:
            return jsonify({'error': 'Failed to update comment or unauthorized'}), 403

        # Get updated comment
        comment = PostModel.get_comment_by_id(conn, comment_id)

        # Process profile image
        if comment and 'profile_image' in comment and comment['profile_image']:
            url = r2_storage.get_file_url(comment['profile_image'], expiration=604800)
            if url:
                comment['profile_image'] = url

        return jsonify({
            'message': 'Comment updated successfully',
            'comment': comment
        }), 200

    except Exception as e:
        print(f"Update comment error: {e}")
        return jsonify({'error': 'Failed to update comment', 'details': str(e)}), 500


@post_bp.route('/comments/<int:comment_id>', methods=['DELETE'])
@token_required
def delete_comment(current_user, comment_id):
    """
    Delete a comment (soft delete - only by owner)

    Path parameters:
        - comment_id: Comment ID
    """
    try:
        # Get database connection
        from app import get_db_connection
        conn = get_db_connection()

        # Delete comment
        success = PostModel.delete_comment(conn, comment_id, current_user['id'])

        if not success:
            return jsonify({'error': 'Failed to delete comment or unauthorized'}), 403

        return jsonify({
            'message': 'Comment deleted successfully'
        }), 200

    except Exception as e:
        print(f"Delete comment error: {e}")
        return jsonify({'error': 'Failed to delete comment', 'details': str(e)}), 500


# ==================== DONATOR ENDPOINTS ====================

@post_bp.route('/donators', methods=['POST'])
@token_required
def create_donator(current_user):
    """
    Create a donator entry with optional proof images

    Form data:
        - post_id (required): Post ID
        - amount (required): Donation amount
        - message (optional): Message from donator
        - proofs[] (files, optional): Multiple proof images
    """
    try:
        # Get form data
        post_id = request.form.get('post_id')
        amount = request.form.get('amount')
        message = request.form.get('message')

        # Validate required fields
        if not all([post_id, amount]):
            return jsonify({
                'error': 'Missing required fields',
                'required': ['post_id', 'amount']
            }), 400

        # Validate amount
        try:
            amount = float(amount)
            if amount <= 0:
                return jsonify({'error': 'Amount must be greater than 0'}), 400
        except (ValueError, TypeError):
            return jsonify({'error': 'Invalid amount'}), 400

        # Get database connection
        from app import get_db_connection
        conn = get_db_connection()

        # Verify post exists
        post = PostModel.get_post_by_id(conn, int(post_id), current_user['id'])
        if not post:
            return jsonify({'error': 'Post not found'}), 404

        # Create donator entry
        donator_id = PostModel.add_donator(conn, int(post_id), current_user['id'], amount, message)

        if not donator_id:
            return jsonify({'error': 'Failed to create donator'}), 500

        # Handle proof image uploads
        proof_paths = []
        if 'proofs' in request.files:
            proofs = request.files.getlist('proofs')
            for proof in proofs:
                if proof and proof.filename != '' and allowed_file(proof.filename, ALLOWED_IMAGE_EXTENSIONS):
                    proof_path = r2_storage.upload_file(proof, 'donators/proofs')
                    if proof_path:
                        # Add proof to database
                        PostModel.add_donator_proof(conn, donator_id, proof_path)
                        proof_paths.append(proof_path)
                        print(f"Donator proof uploaded to: {proof_path}")

        # Get created donator with proofs
        donator = PostModel.get_donator_by_id(conn, donator_id)

        # Process profile image and proof images
        if donator:
            if 'profile_image' in donator and donator['profile_image']:
                url = r2_storage.get_file_url(donator['profile_image'], expiration=604800)
                if url:
                    donator['profile_image'] = url

            # Process proof images
            if 'proofs' in donator:
                for proof in donator['proofs']:
                    if 'image_url' in proof and proof['image_url']:
                        url = r2_storage.get_file_url(proof['image_url'], expiration=604800)
                        if url:
                            proof['image_url'] = url

        return jsonify({
            'message': 'Donator created successfully',
            'donator': donator
        }), 201

    except Exception as e:
        print(f"Create donator error: {e}")
        return jsonify({'error': 'Failed to create donator', 'details': str(e)}), 500


@post_bp.route('/donators', methods=['GET'])
@token_required
def get_donators(current_user):
    """
    Get all donators with optional filters

    Query parameters:
        - post_id (optional): Filter by post
        - verification_status (optional): Filter by status ('pending', 'ongoing', 'fulfilled')
        - limit (optional, default: 50): Number of donators to return
        - offset (optional, default: 0): Offset for pagination
    """
    try:
        # Get query parameters
        post_id = request.args.get('post_id', type=int)
        verification_status = request.args.get('verification_status')
        limit = request.args.get('limit', default=50, type=int)
        offset = request.args.get('offset', default=0, type=int)

        # Build filters
        filters = {}
        if post_id:
            filters['post_id'] = post_id
        if verification_status:
            filters['verification_status'] = verification_status

        # Get database connection
        from app import get_db_connection
        conn = get_db_connection()

        # Get donators
        donators = PostModel.get_all_donators(conn, filters, limit, offset)

        # Process profile images and proof images
        for donator in donators:
            if 'profile_image' in donator and donator['profile_image']:
                url = r2_storage.get_file_url(donator['profile_image'], expiration=604800)
                if url:
                    donator['profile_image'] = url

            # Process proof images
            if 'proofs' in donator:
                for proof in donator['proofs']:
                    if 'image_url' in proof and proof['image_url']:
                        url = r2_storage.get_file_url(proof['image_url'], expiration=604800)
                        if url:
                            proof['image_url'] = url

        return jsonify({
            'donators': donators,
            'count': len(donators),
            'limit': limit,
            'offset': offset
        }), 200

    except Exception as e:
        print(f"Get donators error: {e}")
        return jsonify({'error': 'Failed to get donators', 'details': str(e)}), 500


@post_bp.route('/donators/user/<int:user_id>', methods=['GET'])
@token_required
def get_donators_by_user(current_user, user_id):
    """
    Get donators by user ID

    Path parameters:
        - user_id: User ID

    Query parameters:
        - verification_status (optional): Filter by status
        - limit (optional, default: 50): Number of donators to return
        - offset (optional, default: 0): Offset for pagination
    """
    try:
        # Get query parameters
        verification_status = request.args.get('verification_status')
        limit = request.args.get('limit', default=50, type=int)
        offset = request.args.get('offset', default=0, type=int)

        # Build filters with user_id
        filters = {'user_id': user_id}
        if verification_status:
            filters['verification_status'] = verification_status

        # Get database connection
        from app import get_db_connection
        conn = get_db_connection()

        # Get donators
        donators = PostModel.get_all_donators(conn, filters, limit, offset)

        # Process profile images and proof images
        for donator in donators:
            if 'profile_image' in donator and donator['profile_image']:
                url = r2_storage.get_file_url(donator['profile_image'], expiration=604800)
                if url:
                    donator['profile_image'] = url

            # Process proof images
            if 'proofs' in donator:
                for proof in donator['proofs']:
                    if 'image_url' in proof and proof['image_url']:
                        url = r2_storage.get_file_url(proof['image_url'], expiration=604800)
                        if url:
                            proof['image_url'] = url

        return jsonify({
            'donators': donators,
            'user_id': user_id,
            'count': len(donators),
            'limit': limit,
            'offset': offset
        }), 200

    except Exception as e:
        print(f"Get donators by user error: {e}")
        return jsonify({'error': 'Failed to get donators', 'details': str(e)}), 500


@post_bp.route('/donators/<int:donator_id>', methods=['PUT'])
@token_required
def update_donator(current_user, donator_id):
    """
    Update donator information (only by owner)

    Path parameters:
        - donator_id: Donator ID

    JSON body:
        - amount (optional): Update donation amount
        - verification_status (optional): 'pending', 'ongoing', 'fulfilled'
        - message (optional): Update message
    """
    try:
        data = request.get_json()

        if not data:
            return jsonify({'error': 'No data provided'}), 400

        # Prepare update data
        update_data = {}
        allowed_fields = ['amount', 'verification_status', 'message']

        for field in allowed_fields:
            if field in data:
                if field == 'amount' and data[field] is not None:
                    try:
                        amount = float(data[field])
                        if amount <= 0:
                            return jsonify({'error': 'Amount must be greater than 0'}), 400
                        update_data[field] = amount
                    except (ValueError, TypeError):
                        return jsonify({'error': 'Invalid amount'}), 400
                elif field == 'verification_status':
                    valid_statuses = ['pending', 'ongoing', 'fulfilled']
                    if data[field] not in valid_statuses:
                        return jsonify({
                            'error': 'Invalid verification_status',
                            'allowed_values': valid_statuses
                        }), 400
                    update_data[field] = data[field]
                else:
                    update_data[field] = data[field]

        if not update_data:
            return jsonify({'error': 'No valid fields to update'}), 400

        # Get database connection
        from app import get_db_connection
        conn = get_db_connection()

        # Update donator
        success = PostModel.update_donator(conn, donator_id, current_user['id'], update_data)

        if not success:
            return jsonify({'error': 'Failed to update donator or unauthorized'}), 403

        # Get updated donator
        donator = PostModel.get_donator_by_id(conn, donator_id)

        # Process profile image and proof images
        if donator:
            if 'profile_image' in donator and donator['profile_image']:
                url = r2_storage.get_file_url(donator['profile_image'], expiration=604800)
                if url:
                    donator['profile_image'] = url

            # Process proof images
            if 'proofs' in donator:
                for proof in donator['proofs']:
                    if 'image_url' in proof and proof['image_url']:
                        url = r2_storage.get_file_url(proof['image_url'], expiration=604800)
                        if url:
                            proof['image_url'] = url

        return jsonify({
            'message': 'Donator updated successfully',
            'donator': donator
        }), 200

    except Exception as e:
        print(f"Update donator error: {e}")
        return jsonify({'error': 'Failed to update donator', 'details': str(e)}), 500


# ==================== SUPPORTER ENDPOINTS ====================

@post_bp.route('/supporters', methods=['POST'])
@token_required
def create_supporter(current_user):
    """
    Create a supporter entry with optional proof images

    Form data:
        - post_id (required): Post ID
        - support_type (optional, default: 'share'): 'share', 'volunteer', 'advocate', 'other'
        - message (optional): Message from supporter
        - proofs[] (files, optional): Multiple proof images
    """
    try:
        # Get form data
        post_id = request.form.get('post_id')
        support_type = request.form.get('support_type', 'share')
        message = request.form.get('message')

        # Validate required fields
        if not post_id:
            return jsonify({
                'error': 'Missing required fields',
                'required': ['post_id']
            }), 400

        # Validate support type
        valid_support_types = ['share', 'volunteer', 'advocate', 'other']
        if support_type not in valid_support_types:
            return jsonify({
                'error': 'Invalid support_type',
                'allowed_values': valid_support_types
            }), 400

        # Get database connection
        from app import get_db_connection
        conn = get_db_connection()

        # Verify post exists
        post = PostModel.get_post_by_id(conn, int(post_id), current_user['id'])
        if not post:
            return jsonify({'error': 'Post not found'}), 404

        # Create supporter entry
        supporter_id = PostModel.add_supporter(conn, int(post_id), current_user['id'], support_type, message)

        if not supporter_id:
            return jsonify({'error': 'Failed to create supporter'}), 500

        # Handle proof image uploads
        proof_paths = []
        if 'proofs' in request.files:
            proofs = request.files.getlist('proofs')
            for proof in proofs:
                if proof and proof.filename != '' and allowed_file(proof.filename, ALLOWED_IMAGE_EXTENSIONS):
                    proof_path = r2_storage.upload_file(proof, 'supporters/proofs')
                    if proof_path:
                        # Add proof to database
                        PostModel.add_supporter_proof(conn, supporter_id, proof_path)
                        proof_paths.append(proof_path)
                        print(f"Supporter proof uploaded to: {proof_path}")

        # Get created supporter with proofs
        supporter = PostModel.get_supporter_by_id(conn, supporter_id)

        # Process profile image and proof images
        if supporter:
            if 'profile_image' in supporter and supporter['profile_image']:
                url = r2_storage.get_file_url(supporter['profile_image'], expiration=604800)
                if url:
                    supporter['profile_image'] = url

            # Process proof images
            if 'proofs' in supporter:
                for proof in supporter['proofs']:
                    if 'image_url' in proof and proof['image_url']:
                        url = r2_storage.get_file_url(proof['image_url'], expiration=604800)
                        if url:
                            proof['image_url'] = url

        return jsonify({
            'message': 'Supporter created successfully',
            'supporter': supporter
        }), 201

    except Exception as e:
        print(f"Create supporter error: {e}")
        return jsonify({'error': 'Failed to create supporter', 'details': str(e)}), 500


@post_bp.route('/supporters', methods=['GET'])
@token_required
def get_supporters(current_user):
    """
    Get all supporters with optional filters

    Query parameters:
        - post_id (optional): Filter by post
        - support_type (optional): Filter by type ('share', 'volunteer', 'advocate', 'other')
        - limit (optional, default: 50): Number of supporters to return
        - offset (optional, default: 0): Offset for pagination
    """
    try:
        # Get query parameters
        post_id = request.args.get('post_id', type=int)
        support_type = request.args.get('support_type')
        limit = request.args.get('limit', default=50, type=int)
        offset = request.args.get('offset', default=0, type=int)

        # Build filters
        filters = {}
        if post_id:
            filters['post_id'] = post_id
        if support_type:
            filters['support_type'] = support_type

        # Get database connection
        from app import get_db_connection
        conn = get_db_connection()

        # Get supporters
        supporters = PostModel.get_all_supporters(conn, filters, limit, offset)

        # Process profile images and proof images
        for supporter in supporters:
            if 'profile_image' in supporter and supporter['profile_image']:
                url = r2_storage.get_file_url(supporter['profile_image'], expiration=604800)
                if url:
                    supporter['profile_image'] = url

            # Process proof images
            if 'proofs' in supporter:
                for proof in supporter['proofs']:
                    if 'image_url' in proof and proof['image_url']:
                        url = r2_storage.get_file_url(proof['image_url'], expiration=604800)
                        if url:
                            proof['image_url'] = url

        return jsonify({
            'supporters': supporters,
            'count': len(supporters),
            'limit': limit,
            'offset': offset
        }), 200

    except Exception as e:
        print(f"Get supporters error: {e}")
        return jsonify({'error': 'Failed to get supporters', 'details': str(e)}), 500


@post_bp.route('/supporters/user/<int:user_id>', methods=['GET'])
@token_required
def get_supporters_by_user(current_user, user_id):
    """
    Get supporters by user ID

    Path parameters:
        - user_id: User ID

    Query parameters:
        - support_type (optional): Filter by type
        - limit (optional, default: 50): Number of supporters to return
        - offset (optional, default: 0): Offset for pagination
    """
    try:
        # Get query parameters
        support_type = request.args.get('support_type')
        limit = request.args.get('limit', default=50, type=int)
        offset = request.args.get('offset', default=0, type=int)

        # Build filters with user_id
        filters = {'user_id': user_id}
        if support_type:
            filters['support_type'] = support_type

        # Get database connection
        from app import get_db_connection
        conn = get_db_connection()

        # Get supporters
        supporters = PostModel.get_all_supporters(conn, filters, limit, offset)

        # Process profile images and proof images
        for supporter in supporters:
            if 'profile_image' in supporter and supporter['profile_image']:
                url = r2_storage.get_file_url(supporter['profile_image'], expiration=604800)
                if url:
                    supporter['profile_image'] = url

            # Process proof images
            if 'proofs' in supporter:
                for proof in supporter['proofs']:
                    if 'image_url' in proof and proof['image_url']:
                        url = r2_storage.get_file_url(proof['image_url'], expiration=604800)
                        if url:
                            proof['image_url'] = url

        return jsonify({
            'supporters': supporters,
            'user_id': user_id,
            'count': len(supporters),
            'limit': limit,
            'offset': offset
        }), 200

    except Exception as e:
        print(f"Get supporters by user error: {e}")
        return jsonify({'error': 'Failed to get supporters', 'details': str(e)}), 500


@post_bp.route('/supporters/<int:supporter_id>', methods=['PUT'])
@token_required
def update_supporter(current_user, supporter_id):
    """
    Update supporter information (only by owner)

    Path parameters:
        - supporter_id: Supporter ID

    JSON body:
        - support_type (optional): 'share', 'volunteer', 'advocate', 'other'
        - message (optional): Update message
    """
    try:
        data = request.get_json()

        if not data:
            return jsonify({'error': 'No data provided'}), 400

        # Prepare update data
        update_data = {}
        allowed_fields = ['support_type', 'message']

        for field in allowed_fields:
            if field in data:
                if field == 'support_type':
                    valid_support_types = ['share', 'volunteer', 'advocate', 'other']
                    if data[field] not in valid_support_types:
                        return jsonify({
                            'error': 'Invalid support_type',
                            'allowed_values': valid_support_types
                        }), 400
                    update_data[field] = data[field]
                else:
                    update_data[field] = data[field]

        if not update_data:
            return jsonify({'error': 'No valid fields to update'}), 400

        # Get database connection
        from app import get_db_connection
        conn = get_db_connection()

        # Update supporter
        success = PostModel.update_supporter(conn, supporter_id, current_user['id'], update_data)

        if not success:
            return jsonify({'error': 'Failed to update supporter or unauthorized'}), 403

        # Get updated supporter
        supporter = PostModel.get_supporter_by_id(conn, supporter_id)

        # Process profile image and proof images
        if supporter:
            if 'profile_image' in supporter and supporter['profile_image']:
                url = r2_storage.get_file_url(supporter['profile_image'], expiration=604800)
                if url:
                    supporter['profile_image'] = url

            # Process proof images
            if 'proofs' in supporter:
                for proof in supporter['proofs']:
                    if 'image_url' in proof and proof['image_url']:
                        url = r2_storage.get_file_url(proof['image_url'], expiration=604800)
                        if url:
                            proof['image_url'] = url

        return jsonify({
            'message': 'Supporter updated successfully',
            'supporter': supporter
        }), 200

    except Exception as e:
        print(f"Update supporter error: {e}")
        return jsonify({'error': 'Failed to update supporter', 'details': str(e)}), 500

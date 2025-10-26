from flask import Blueprint, request, jsonify

from models.chat_model import ChatModel
from routes.auth import token_required
from utils.r2_storage import r2_storage

chat_bp = Blueprint('chat', __name__)

# Allowed file extensions
ALLOWED_IMAGE_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}
ALLOWED_VIDEO_EXTENSIONS = {'mp4', 'mov', 'avi', 'webm'}


def allowed_file(filename, allowed_extensions):
    """Check if file extension is allowed"""
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in allowed_extensions


def process_media_urls(media_list):
    """
    Convert media paths to full URLs using R2 storage presigned URLs

    Args:
        media_list: List of media dictionaries with media_url

    Returns:
        List with media URLs converted to presigned URLs
    """
    if not media_list:
        return media_list

    for media in media_list:
        if 'media_url' in media and media['media_url']:
            url = r2_storage.get_file_url(media['media_url'], expiration=604800)
            if url:
                media['media_url'] = url

        if 'thumbnail_url' in media and media['thumbnail_url']:
            url = r2_storage.get_file_url(media['thumbnail_url'], expiration=604800)
            if url:
                media['thumbnail_url'] = url

    return media_list


def process_user_profile_images(items):
    """
    Process profile images in a list of items

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


@chat_bp.route('', methods=['POST'])
@token_required
def create_chat(current_user):
    """
    Create a new chat (group) or get/create private chat

    JSON body:
        - type (required): 'private' or 'group'
        - participant_ids (required for private, optional for group): List of user IDs
    """
    try:
        data = request.get_json()

        if not data:
            return jsonify({'error': 'No data provided'}), 400

        chat_type = data.get('type', 'private')
        participant_ids = data.get('participant_ids', [])

        # Validate chat type
        if chat_type not in ['private', 'group']:
            return jsonify({
                'error': 'Invalid chat type',
                'allowed_values': ['private', 'group']
            }), 400

        # Get database connection
        from app import get_db_connection
        conn = get_db_connection()

        # Handle private chat
        if chat_type == 'private':
            if len(participant_ids) != 1:
                return jsonify({'error': 'Private chat requires exactly one other participant'}), 400

            other_user_id = participant_ids[0]

            # Get or create private chat
            chat_id = ChatModel.get_or_create_private_chat(conn, current_user['id'], other_user_id)

            if not chat_id:
                return jsonify({'error': 'Failed to create chat'}), 500

        # Handle group chat
        else:
            # Create chat
            chat_id = ChatModel.create_chat(conn, chat_type)

            if not chat_id:
                return jsonify({'error': 'Failed to create chat'}), 500

            # Add current user as participant
            ChatModel.add_participant(conn, chat_id, current_user['id'])

            # Add other participants
            for participant_id in participant_ids:
                ChatModel.add_participant(conn, chat_id, participant_id)

        # Get created chat
        chat = ChatModel.get_chat_by_id(conn, chat_id, current_user['id'])

        # Process profile images
        if chat and 'participants' in chat:
            chat['participants'] = process_user_profile_images(chat['participants'])

        return jsonify({
            'message': 'Chat created successfully',
            'chat': chat
        }), 201

    except Exception as e:
        print(f"Create chat error: {e}")
        return jsonify({'error': 'Failed to create chat', 'details': str(e)}), 500


@chat_bp.route('', methods=['GET'])
@token_required
def get_chats(current_user):
    """
    Get all chats for current user

    Query parameters:
        - limit (optional, default: 50): Number of chats to return
        - offset (optional, default: 0): Offset for pagination
    """
    try:
        # Get query parameters
        limit = request.args.get('limit', default=50, type=int)
        offset = request.args.get('offset', default=0, type=int)

        # Get database connection
        from app import get_db_connection
        conn = get_db_connection()

        # Get chats
        chats = ChatModel.get_user_chats(conn, current_user['id'], limit, offset)

        # Process profile images for all participants
        for chat in chats:
            if 'participants' in chat:
                chat['participants'] = process_user_profile_images(chat['participants'])

        return jsonify({
            'chats': chats,
            'count': len(chats),
            'limit': limit,
            'offset': offset
        }), 200

    except Exception as e:
        print(f"Get chats error: {e}")
        return jsonify({'error': 'Failed to get chats', 'details': str(e)}), 500


@chat_bp.route('/<int:chat_id>', methods=['GET'])
@token_required
def get_chat(current_user, chat_id):
    """
    Get a single chat by ID

    Path parameters:
        - chat_id: Chat ID
    """
    try:
        # Get database connection
        from app import get_db_connection
        conn = get_db_connection()

        # Get chat
        chat = ChatModel.get_chat_by_id(conn, chat_id, current_user['id'])

        if not chat:
            return jsonify({'error': 'Chat not found or unauthorized'}), 404

        # Process profile images
        if 'participants' in chat:
            chat['participants'] = process_user_profile_images(chat['participants'])

        return jsonify({
            'chat': chat
        }), 200

    except Exception as e:
        print(f"Get chat error: {e}")
        return jsonify({'error': 'Failed to get chat', 'details': str(e)}), 500


@chat_bp.route('/<int:chat_id>/messages', methods=['POST'])
@token_required
def send_message(current_user, chat_id):
    """
    Send a message in a chat

    Path parameters:
        - chat_id: Chat ID

    Form data (for text):
        - content (required): Message text

    Form data (for photo/video):
        - content (optional): Caption/text
        - message_type (required): 'photo' or 'video'
        - media[] (files, required for photo/video): Media files
    """
    try:
        # Get database connection
        from app import get_db_connection
        conn = get_db_connection()

        # Verify user is participant
        chat = ChatModel.get_chat_by_id(conn, chat_id, current_user['id'])
        if not chat:
            return jsonify({'error': 'Chat not found or unauthorized'}), 404

        # Determine message type
        message_type = request.form.get('message_type', 'text')
        content = request.form.get('content', '')

        # Validate message type
        valid_types = ['text', 'photo', 'video']
        if message_type not in valid_types:
            return jsonify({
                'error': 'Invalid message_type',
                'allowed_values': valid_types
            }), 400

        # For text messages, content is required
        if message_type == 'text' and not content:
            return jsonify({'error': 'Content is required for text messages'}), 400

        # Create message
        message_id = ChatModel.create_message(conn, chat_id, current_user['id'], content, message_type)

        if not message_id:
            return jsonify({'error': 'Failed to send message'}), 500

        # Handle media uploads for photo/video messages
        if message_type in ['photo', 'video']:
            media_field = 'media'
            if media_field not in request.files:
                return jsonify({'error': f'Media files required for {message_type} messages'}), 400

            media_files = request.files.getlist(media_field)
            allowed_extensions = ALLOWED_IMAGE_EXTENSIONS if message_type == 'photo' else ALLOWED_VIDEO_EXTENSIONS
            folder = f'chats/{message_type}s'

            for media_file in media_files:
                if media_file and media_file.filename != '' and allowed_file(media_file.filename, allowed_extensions):
                    media_path = r2_storage.upload_file(media_file, folder)
                    if media_path:
                        # Add media to database
                        ChatModel.add_message_media(conn, message_id, message_type, media_path)
                        print(f"Message media uploaded to: {media_path}")

        # Get created message with media
        messages = ChatModel.get_chat_messages(conn, chat_id, current_user['id'], limit=1, offset=0)

        if messages:
            message = messages[0]

            # Process profile image
            if 'profile_image' in message and message['profile_image']:
                url = r2_storage.get_file_url(message['profile_image'], expiration=604800)
                if url:
                    message['profile_image'] = url

            # Process media URLs
            if 'media' in message:
                message['media'] = process_media_urls(message['media'])

            return jsonify({
                'message': 'Message sent successfully',
                'data': message
            }), 201

        return jsonify({'message': 'Message sent successfully'}), 201

    except Exception as e:
        print(f"Send message error: {e}")
        return jsonify({'error': 'Failed to send message', 'details': str(e)}), 500


@chat_bp.route('/<int:chat_id>/messages', methods=['GET'])
@token_required
def get_messages(current_user, chat_id):
    """
    Get messages for a chat

    Path parameters:
        - chat_id: Chat ID

    Query parameters:
        - limit (optional, default: 50): Number of messages to return
        - offset (optional, default: 0): Offset for pagination
    """
    try:
        # Get query parameters
        limit = request.args.get('limit', default=50, type=int)
        offset = request.args.get('offset', default=0, type=int)

        # Get database connection
        from app import get_db_connection
        conn = get_db_connection()

        # Get messages
        messages = ChatModel.get_chat_messages(conn, chat_id, current_user['id'], limit, offset)

        if messages is None:
            return jsonify({'error': 'Chat not found or unauthorized'}), 404

        # Process profile images and media URLs
        for message in messages:
            if 'profile_image' in message and message['profile_image']:
                url = r2_storage.get_file_url(message['profile_image'], expiration=604800)
                if url:
                    message['profile_image'] = url

            # Process media URLs
            if 'media' in message:
                message['media'] = process_media_urls(message['media'])

        return jsonify({
            'messages': messages,
            'count': len(messages),
            'limit': limit,
            'offset': offset
        }), 200

    except Exception as e:
        print(f"Get messages error: {e}")
        return jsonify({'error': 'Failed to get messages', 'details': str(e)}), 500


@chat_bp.route('/<int:chat_id>/messages/seen', methods=['PUT'])
@token_required
def mark_messages_seen(current_user, chat_id):
    """
    Mark all messages in a chat as seen

    Path parameters:
        - chat_id: Chat ID
    """
    try:
        # Get database connection
        from app import get_db_connection
        conn = get_db_connection()

        # Verify user is participant
        chat = ChatModel.get_chat_by_id(conn, chat_id, current_user['id'])
        if not chat:
            return jsonify({'error': 'Chat not found or unauthorized'}), 404

        # Mark messages as seen
        success = ChatModel.mark_chat_messages_as_seen(conn, chat_id, current_user['id'])

        if not success:
            return jsonify({'error': 'Failed to mark messages as seen'}), 500

        return jsonify({
            'message': 'Messages marked as seen'
        }), 200

    except Exception as e:
        print(f"Mark messages seen error: {e}")
        return jsonify({'error': 'Failed to mark messages as seen', 'details': str(e)}), 500


@chat_bp.route('/<int:chat_id>/participants', methods=['POST'])
@token_required
def add_participant(current_user, chat_id):
    """
    Add a participant to a group chat

    Path parameters:
        - chat_id: Chat ID

    JSON body:
        - user_id (required): User ID to add
    """
    try:
        data = request.get_json()

        if not data:
            return jsonify({'error': 'No data provided'}), 400

        user_id = data.get('user_id')

        if not user_id:
            return jsonify({'error': 'user_id is required'}), 400

        # Get database connection
        from app import get_db_connection
        conn = get_db_connection()

        # Verify user is participant and chat is group
        chat = ChatModel.get_chat_by_id(conn, chat_id, current_user['id'])
        if not chat:
            return jsonify({'error': 'Chat not found or unauthorized'}), 404

        if chat['type'] != 'group':
            return jsonify({'error': 'Can only add participants to group chats'}), 400

        # Add participant
        success = ChatModel.add_participant(conn, chat_id, user_id)

        if not success:
            return jsonify({'error': 'Failed to add participant or already member'}), 400

        return jsonify({
            'message': 'Participant added successfully'
        }), 200

    except Exception as e:
        print(f"Add participant error: {e}")
        return jsonify({'error': 'Failed to add participant', 'details': str(e)}), 500

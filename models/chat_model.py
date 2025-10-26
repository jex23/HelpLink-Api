import pymysql


class ChatModel:
    """Chat model for messaging operations"""

    @staticmethod
    def create_chat(connection, chat_type='private'):
        """
        Create a new chat

        Args:
            connection: Database connection
            chat_type: 'private' or 'group'

        Returns:
            int: Chat ID if successful, None otherwise
        """
        try:
            with connection.cursor() as cursor:
                sql = "INSERT INTO chats (type) VALUES (%s)"
                cursor.execute(sql, (chat_type,))
                connection.commit()
                return cursor.lastrowid
        except Exception as e:
            connection.rollback()
            print(f"Error creating chat: {e}")
            return None

    @staticmethod
    def add_participant(connection, chat_id, user_id):
        """
        Add a participant to a chat

        Args:
            connection: Database connection
            chat_id: Chat's ID
            user_id: User's ID

        Returns:
            bool: True if successful, False otherwise
        """
        try:
            with connection.cursor() as cursor:
                sql = "INSERT INTO chat_participants (chat_id, user_id) VALUES (%s, %s)"
                cursor.execute(sql, (chat_id, user_id))
                connection.commit()
                return True
        except pymysql.IntegrityError:
            connection.rollback()
            return False
        except Exception as e:
            connection.rollback()
            print(f"Error adding participant: {e}")
            return False

    @staticmethod
    def get_user_chats(connection, user_id, limit=50, offset=0):
        """
        Get all chats for a user

        Args:
            connection: Database connection
            user_id: User's ID
            limit: Number of chats to return
            offset: Offset for pagination

        Returns:
            list: List of chats or empty list
        """
        try:
            with connection.cursor() as cursor:
                sql = """
                    SELECT
                        c.*,
                        m.content as last_message_content,
                        m.message_type as last_message_type,
                        m.created_at as last_message_time,
                        sender.first_name as last_sender_first_name,
                        sender.last_name as last_sender_last_name
                    FROM chats c
                    INNER JOIN chat_participants cp ON c.id = cp.chat_id
                    LEFT JOIN messages m ON c.last_message_id = m.id
                    LEFT JOIN users sender ON m.sender_id = sender.id
                    WHERE cp.user_id = %s
                    ORDER BY c.created_at DESC
                    LIMIT %s OFFSET %s
                """
                cursor.execute(sql, (user_id, limit, offset))
                chats = cursor.fetchall()

                # Get participants for each chat
                for chat in chats:
                    cursor.execute("""
                        SELECT
                            u.id, u.first_name, u.last_name, u.profile_image,
                            cp.joined_at
                        FROM chat_participants cp
                        LEFT JOIN users u ON cp.user_id = u.id
                        WHERE cp.chat_id = %s
                    """, (chat['id'],))
                    chat['participants'] = cursor.fetchall()

                return chats
        except Exception as e:
            print(f"Error getting user chats: {e}")
            return []

    @staticmethod
    def get_chat_by_id(connection, chat_id, user_id):
        """
        Get chat by ID (only if user is participant)

        Args:
            connection: Database connection
            chat_id: Chat's ID
            user_id: User's ID

        Returns:
            dict: Chat data or None if not found
        """
        try:
            with connection.cursor() as cursor:
                # Check if user is participant
                cursor.execute(
                    "SELECT id FROM chat_participants WHERE chat_id = %s AND user_id = %s",
                    (chat_id, user_id)
                )
                if not cursor.fetchone():
                    return None

                # Get chat
                sql = """
                    SELECT
                        c.*,
                        m.content as last_message_content,
                        m.message_type as last_message_type,
                        m.created_at as last_message_time
                    FROM chats c
                    LEFT JOIN messages m ON c.last_message_id = m.id
                    WHERE c.id = %s
                """
                cursor.execute(sql, (chat_id,))
                chat = cursor.fetchone()

                if not chat:
                    return None

                # Get participants
                cursor.execute("""
                    SELECT
                        u.id, u.first_name, u.last_name, u.profile_image,
                        cp.joined_at
                    FROM chat_participants cp
                    LEFT JOIN users u ON cp.user_id = u.id
                    WHERE cp.chat_id = %s
                """, (chat_id,))
                chat['participants'] = cursor.fetchall()

                return chat
        except Exception as e:
            print(f"Error getting chat: {e}")
            return None

    @staticmethod
    def create_message(connection, chat_id, sender_id, content, message_type='text'):
        """
        Create a new message

        Args:
            connection: Database connection
            chat_id: Chat's ID
            sender_id: Sender's user ID
            content: Message content (text)
            message_type: 'text', 'photo', 'video'

        Returns:
            int: Message ID if successful, None otherwise
        """
        try:
            with connection.cursor() as cursor:
                # Insert message
                sql = """
                    INSERT INTO messages (chat_id, sender_id, content, message_type)
                    VALUES (%s, %s, %s, %s)
                """
                cursor.execute(sql, (chat_id, sender_id, content, message_type))
                message_id = cursor.lastrowid

                # Update last_message_id in chats table
                cursor.execute(
                    "UPDATE chats SET last_message_id = %s WHERE id = %s",
                    (message_id, chat_id)
                )

                # Create message status for all participants except sender
                cursor.execute(
                    "SELECT user_id FROM chat_participants WHERE chat_id = %s AND user_id != %s",
                    (chat_id, sender_id)
                )
                participants = cursor.fetchall()

                for participant in participants:
                    cursor.execute(
                        "INSERT INTO message_status (message_id, user_id, status) VALUES (%s, %s, 'sent')",
                        (message_id, participant['user_id'])
                    )

                connection.commit()
                return message_id
        except Exception as e:
            connection.rollback()
            print(f"Error creating message: {e}")
            return None

    @staticmethod
    def add_message_media(connection, message_id, media_type, media_url, thumbnail_url=None):
        """
        Add media to a message

        Args:
            connection: Database connection
            message_id: Message's ID
            media_type: 'photo' or 'video'
            media_url: URL/path of the media
            thumbnail_url: URL/path of thumbnail (optional)

        Returns:
            int: Media ID if successful, None otherwise
        """
        try:
            with connection.cursor() as cursor:
                sql = """
                    INSERT INTO message_media (message_id, media_type, media_url, thumbnail_url)
                    VALUES (%s, %s, %s, %s)
                """
                cursor.execute(sql, (message_id, media_type, media_url, thumbnail_url))
                connection.commit()
                return cursor.lastrowid
        except Exception as e:
            connection.rollback()
            print(f"Error adding message media: {e}")
            return None

    @staticmethod
    def get_chat_messages(connection, chat_id, user_id, limit=50, offset=0):
        """
        Get messages for a chat

        Args:
            connection: Database connection
            chat_id: Chat's ID
            user_id: Current user's ID (to check participation)
            limit: Number of messages to return
            offset: Offset for pagination

        Returns:
            list: List of messages or empty list
        """
        try:
            with connection.cursor() as cursor:
                # Check if user is participant
                cursor.execute(
                    "SELECT id FROM chat_participants WHERE chat_id = %s AND user_id = %s",
                    (chat_id, user_id)
                )
                if not cursor.fetchone():
                    return []

                # Get messages
                sql = """
                    SELECT
                        m.*,
                        u.first_name, u.last_name, u.profile_image
                    FROM messages m
                    LEFT JOIN users u ON m.sender_id = u.id
                    WHERE m.chat_id = %s
                    ORDER BY m.created_at DESC
                    LIMIT %s OFFSET %s
                """
                cursor.execute(sql, (chat_id, limit, offset))
                messages = cursor.fetchall()

                # Get media for each message
                for message in messages:
                    cursor.execute(
                        "SELECT * FROM message_media WHERE message_id = %s",
                        (message['id'],)
                    )
                    message['media'] = cursor.fetchall()

                    # Get status for current user
                    cursor.execute(
                        "SELECT status, seen_at FROM message_status WHERE message_id = %s AND user_id = %s",
                        (message['id'], user_id)
                    )
                    status = cursor.fetchone()
                    message['status'] = status['status'] if status else 'seen'
                    message['seen_at'] = status['seen_at'] if status else None

                return messages
        except Exception as e:
            print(f"Error getting messages: {e}")
            return []

    @staticmethod
    def update_message_status(connection, message_id, user_id, status='seen'):
        """
        Update message status for a user

        Args:
            connection: Database connection
            message_id: Message's ID
            user_id: User's ID
            status: 'sent', 'delivered', 'seen'

        Returns:
            bool: True if successful, False otherwise
        """
        try:
            with connection.cursor() as cursor:
                sql = """
                    UPDATE message_status
                    SET status = %s, seen_at = CASE WHEN %s = 'seen' THEN CURRENT_TIMESTAMP ELSE seen_at END
                    WHERE message_id = %s AND user_id = %s
                """
                cursor.execute(sql, (status, status, message_id, user_id))
                connection.commit()
                return True
        except Exception as e:
            connection.rollback()
            print(f"Error updating message status: {e}")
            return False

    @staticmethod
    def mark_chat_messages_as_seen(connection, chat_id, user_id):
        """
        Mark all messages in a chat as seen for a user

        Args:
            connection: Database connection
            chat_id: Chat's ID
            user_id: User's ID

        Returns:
            bool: True if successful, False otherwise
        """
        try:
            with connection.cursor() as cursor:
                sql = """
                    UPDATE message_status ms
                    INNER JOIN messages m ON ms.message_id = m.id
                    SET ms.status = 'seen', ms.seen_at = CURRENT_TIMESTAMP
                    WHERE m.chat_id = %s AND ms.user_id = %s AND ms.status != 'seen'
                """
                cursor.execute(sql, (chat_id, user_id))
                connection.commit()
                return True
        except Exception as e:
            connection.rollback()
            print(f"Error marking messages as seen: {e}")
            return False

    @staticmethod
    def get_or_create_private_chat(connection, user1_id, user2_id):
        """
        Get existing private chat between two users or create new one

        Args:
            connection: Database connection
            user1_id: First user's ID
            user2_id: Second user's ID

        Returns:
            int: Chat ID if successful, None otherwise
        """
        try:
            with connection.cursor() as cursor:
                # Find existing private chat with exactly these two participants
                sql = """
                    SELECT c.id
                    FROM chats c
                    WHERE c.type = 'private'
                    AND (
                        SELECT COUNT(DISTINCT cp.user_id)
                        FROM chat_participants cp
                        WHERE cp.chat_id = c.id
                        AND cp.user_id IN (%s, %s)
                    ) = 2
                    AND (
                        SELECT COUNT(*)
                        FROM chat_participants cp
                        WHERE cp.chat_id = c.id
                    ) = 2
                    LIMIT 1
                """
                cursor.execute(sql, (user1_id, user2_id))
                chat = cursor.fetchone()

                if chat:
                    return chat['id']

                # Create new private chat
                cursor.execute("INSERT INTO chats (type) VALUES ('private')")
                chat_id = cursor.lastrowid

                # Add both participants
                cursor.execute(
                    "INSERT INTO chat_participants (chat_id, user_id) VALUES (%s, %s)",
                    (chat_id, user1_id)
                )
                cursor.execute(
                    "INSERT INTO chat_participants (chat_id, user_id) VALUES (%s, %s)",
                    (chat_id, user2_id)
                )

                connection.commit()
                return chat_id
        except Exception as e:
            connection.rollback()
            print(f"Error getting/creating private chat: {e}")
            return None

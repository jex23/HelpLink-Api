import pymysql


class PostModel:
    """Post model for social media operations"""

    @staticmethod
    def create_post(connection, post_data):
        """
        Create a new post in the database

        Args:
            connection: Database connection
            post_data: Dictionary containing post information
                - user_id (required)
                - post_type (required): 'donation' or 'request'
                - title (required)
                - description (optional)
                - address (optional)
                - latitude (optional)
                - longitude (optional)
                - status (optional, default: 'active')
                - photos (optional): List of photo URLs
                - videos (optional): List of video URLs

        Returns:
            int: Post ID if successful, None otherwise
        """
        try:
            with connection.cursor() as cursor:
                # Insert post
                sql = """
                    INSERT INTO posts (
                        user_id, post_type, title, description, address,
                        latitude, longitude, status
                    ) VALUES (
                        %s, %s, %s, %s, %s, %s, %s, %s
                    )
                """
                cursor.execute(sql, (
                    post_data.get('user_id'),
                    post_data.get('post_type'),
                    post_data.get('title'),
                    post_data.get('description'),
                    post_data.get('address'),
                    post_data.get('latitude'),
                    post_data.get('longitude'),
                    post_data.get('status', 'active')
                ))
                post_id = cursor.lastrowid

                # Insert photos if provided
                photos = post_data.get('photos', [])
                if photos:
                    photo_sql = "INSERT INTO post_photos (post_id, photo_url) VALUES (%s, %s)"
                    for photo_url in photos:
                        cursor.execute(photo_sql, (post_id, photo_url))

                # Insert videos if provided
                videos = post_data.get('videos', [])
                if videos:
                    video_sql = "INSERT INTO post_videos (post_id, video_url) VALUES (%s, %s)"
                    for video_url in videos:
                        cursor.execute(video_sql, (post_id, video_url))

                connection.commit()
                return post_id
        except pymysql.IntegrityError as e:
            connection.rollback()
            print(f"Integrity error creating post: {e}")
            return None
        except Exception as e:
            connection.rollback()
            print(f"Error creating post: {e}")
            return None

    @staticmethod
    def get_post_by_id(connection, post_id, current_user_id=None):
        """
        Get post by ID with all related data

        Args:
            connection: Database connection
            post_id: Post's ID
            current_user_id: ID of current user (to check reaction status)

        Returns:
            dict: Post data with photos, videos, reactions, etc., or None if not found
        """
        try:
            with connection.cursor() as cursor:
                # Get post with user info
                sql = """
                    SELECT
                        p.*,
                        u.first_name, u.last_name, u.profile_image,
                        COUNT(DISTINCT pr.id) as reaction_count,
                        COUNT(DISTINCT d.id) as donator_count,
                        COUNT(DISTINCT s.id) as supporter_count,
                        COUNT(DISTINCT c.id) as comment_count
                    FROM posts p
                    LEFT JOIN users u ON p.user_id = u.id
                    LEFT JOIN post_reactions pr ON p.id = pr.post_id
                    LEFT JOIN donators d ON p.id = d.post_id
                    LEFT JOIN supporters s ON p.id = s.post_id
                    LEFT JOIN comments c ON p.id = c.post_id AND c.status = 'visible'
                    WHERE p.id = %s
                    GROUP BY p.id
                """
                cursor.execute(sql, (post_id,))
                post = cursor.fetchone()

                if not post:
                    return None

                # Get photos
                cursor.execute(
                    "SELECT photo_url FROM post_photos WHERE post_id = %s ORDER BY id",
                    (post_id,)
                )
                post['photos'] = [row['photo_url'] for row in cursor.fetchall()]

                # Get videos
                cursor.execute(
                    "SELECT video_url FROM post_videos WHERE post_id = %s ORDER BY id",
                    (post_id,)
                )
                post['videos'] = [row['video_url'] for row in cursor.fetchall()]

                # Check if current user has reacted
                if current_user_id:
                    cursor.execute(
                        "SELECT reaction_type FROM post_reactions WHERE post_id = %s AND user_id = %s",
                        (post_id, current_user_id)
                    )
                    reaction = cursor.fetchone()
                    post['user_reaction'] = reaction['reaction_type'] if reaction else None
                else:
                    post['user_reaction'] = None

                return post
        except Exception as e:
            print(f"Error fetching post: {e}")
            return None

    @staticmethod
    def get_posts(connection, filters=None, current_user_id=None, limit=20, offset=0):
        """
        Get posts with optional filters

        Args:
            connection: Database connection
            filters: Dictionary with optional filters
                - user_id: Filter by user
                - post_type: Filter by type ('donation' or 'request')
                - status: Filter by status
            current_user_id: ID of current user (to check reaction status)
            limit: Number of posts to return
            offset: Offset for pagination

        Returns:
            list: List of posts or empty list
        """
        try:
            with connection.cursor() as cursor:
                # Build query with filters
                where_clauses = []
                params = []

                if filters:
                    if filters.get('user_id'):
                        where_clauses.append("p.user_id = %s")
                        params.append(filters['user_id'])
                    if filters.get('post_type'):
                        where_clauses.append("p.post_type = %s")
                        params.append(filters['post_type'])
                    if filters.get('status'):
                        where_clauses.append("p.status = %s")
                        params.append(filters['status'])

                where_sql = "WHERE " + " AND ".join(where_clauses) if where_clauses else ""

                sql = f"""
                    SELECT
                        p.*,
                        u.first_name, u.last_name, u.profile_image,
                        COUNT(DISTINCT pr.id) as reaction_count,
                        COUNT(DISTINCT d.id) as donator_count,
                        COUNT(DISTINCT s.id) as supporter_count,
                        COUNT(DISTINCT c.id) as comment_count
                    FROM posts p
                    LEFT JOIN users u ON p.user_id = u.id
                    LEFT JOIN post_reactions pr ON p.id = pr.post_id
                    LEFT JOIN donators d ON p.id = d.post_id
                    LEFT JOIN supporters s ON p.id = s.post_id
                    LEFT JOIN comments c ON p.id = c.post_id AND c.status = 'visible'
                    {where_sql}
                    GROUP BY p.id
                    ORDER BY p.created_at DESC
                    LIMIT %s OFFSET %s
                """
                params.extend([limit, offset])
                cursor.execute(sql, tuple(params))
                posts = cursor.fetchall()

                # Get photos and videos for each post
                for post in posts:
                    # Get photos
                    cursor.execute(
                        "SELECT photo_url FROM post_photos WHERE post_id = %s ORDER BY id",
                        (post['id'],)
                    )
                    post['photos'] = [row['photo_url'] for row in cursor.fetchall()]

                    # Get videos
                    cursor.execute(
                        "SELECT video_url FROM post_videos WHERE post_id = %s ORDER BY id",
                        (post['id'],)
                    )
                    post['videos'] = [row['video_url'] for row in cursor.fetchall()]

                    # Check if current user has reacted
                    if current_user_id:
                        cursor.execute(
                            "SELECT reaction_type FROM post_reactions WHERE post_id = %s AND user_id = %s",
                            (post['id'], current_user_id)
                        )
                        reaction = cursor.fetchone()
                        post['user_reaction'] = reaction['reaction_type'] if reaction else None
                    else:
                        post['user_reaction'] = None

                return posts
        except Exception as e:
            print(f"Error fetching posts: {e}")
            return []

    @staticmethod
    def update_post(connection, post_id, user_id, update_data):
        """
        Update post information (only by owner)

        Args:
            connection: Database connection
            post_id: Post's ID
            user_id: User's ID (must be post owner)
            update_data: Dictionary containing fields to update

        Returns:
            bool: True if successful, False otherwise
        """
        try:
            if not update_data:
                return False

            # Check if user is the post owner
            with connection.cursor() as cursor:
                cursor.execute("SELECT user_id FROM posts WHERE id = %s", (post_id,))
                post = cursor.fetchone()

                if not post or post['user_id'] != user_id:
                    return False

                # Build dynamic SQL query based on fields to update
                allowed_fields = ['title', 'description', 'address', 'latitude', 'longitude']
                set_clauses = []
                values = []

                for key, value in update_data.items():
                    if key in allowed_fields:
                        set_clauses.append(f"{key} = %s")
                        values.append(value)

                if not set_clauses:
                    return False

                # Add post_id to the end of values
                values.append(post_id)

                sql = f"UPDATE posts SET {', '.join(set_clauses)} WHERE id = %s"
                cursor.execute(sql, tuple(values))
                connection.commit()
                return True
        except Exception as e:
            connection.rollback()
            print(f"Error updating post: {e}")
            return False

    @staticmethod
    def close_post(connection, post_id, user_id):
        """
        Close a post (update status to 'closed')

        Args:
            connection: Database connection
            post_id: Post's ID
            user_id: User's ID (must be post owner)

        Returns:
            bool: True if successful, False otherwise
        """
        try:
            with connection.cursor() as cursor:
                # Check if user is the post owner
                cursor.execute("SELECT user_id FROM posts WHERE id = %s", (post_id,))
                post = cursor.fetchone()

                if not post or post['user_id'] != user_id:
                    return False

                # Update status to closed
                sql = "UPDATE posts SET status = 'closed' WHERE id = %s"
                cursor.execute(sql, (post_id,))
                connection.commit()
                return True
        except Exception as e:
            connection.rollback()
            print(f"Error closing post: {e}")
            return False

    @staticmethod
    def add_reaction(connection, post_id, user_id, reaction_type='like'):
        """
        Add or update a reaction to a post

        Args:
            connection: Database connection
            post_id: Post's ID
            user_id: User's ID
            reaction_type: Type of reaction ('like', 'love', 'care', 'support')

        Returns:
            bool: True if successful, False otherwise
        """
        try:
            with connection.cursor() as cursor:
                sql = """
                    INSERT INTO post_reactions (post_id, user_id, reaction_type)
                    VALUES (%s, %s, %s)
                    ON DUPLICATE KEY UPDATE reaction_type = VALUES(reaction_type)
                """
                cursor.execute(sql, (post_id, user_id, reaction_type))
                connection.commit()
                return True
        except Exception as e:
            connection.rollback()
            print(f"Error adding reaction: {e}")
            return False

    @staticmethod
    def remove_reaction(connection, post_id, user_id):
        """
        Remove a reaction from a post

        Args:
            connection: Database connection
            post_id: Post's ID
            user_id: User's ID

        Returns:
            bool: True if successful, False otherwise
        """
        try:
            with connection.cursor() as cursor:
                sql = "DELETE FROM post_reactions WHERE post_id = %s AND user_id = %s"
                cursor.execute(sql, (post_id, user_id))
                connection.commit()
                return True
        except Exception as e:
            connection.rollback()
            print(f"Error removing reaction: {e}")
            return False

    @staticmethod
    def add_donator(connection, post_id, user_id, amount, message=None):
        """
        Add a donator to a post

        Args:
            connection: Database connection
            post_id: Post's ID
            user_id: User's ID
            amount: Donation amount
            message: Optional message

        Returns:
            int: Donator ID if successful, None otherwise
        """
        try:
            with connection.cursor() as cursor:
                sql = """
                    INSERT INTO donators (post_id, user_id, amount, message)
                    VALUES (%s, %s, %s, %s)
                """
                cursor.execute(sql, (post_id, user_id, amount, message))
                connection.commit()
                return cursor.lastrowid
        except Exception as e:
            connection.rollback()
            print(f"Error adding donator: {e}")
            return None

    @staticmethod
    def add_supporter(connection, post_id, user_id, support_type='share', message=None):
        """
        Add a supporter to a post

        Args:
            connection: Database connection
            post_id: Post's ID
            user_id: User's ID
            support_type: Type of support ('share', 'volunteer', 'advocate', 'other')
            message: Optional message

        Returns:
            int: Supporter ID if successful, None otherwise
        """
        try:
            with connection.cursor() as cursor:
                sql = """
                    INSERT INTO supporters (post_id, user_id, support_type, message)
                    VALUES (%s, %s, %s, %s)
                """
                cursor.execute(sql, (post_id, user_id, support_type, message))
                connection.commit()
                return cursor.lastrowid
        except Exception as e:
            connection.rollback()
            print(f"Error adding supporter: {e}")
            return None

    @staticmethod
    def delete_post(connection, post_id, user_id):
        """
        Delete a post and all related data (only by owner)

        Args:
            connection: Database connection
            post_id: Post's ID
            user_id: User's ID (must be post owner)

        Returns:
            bool: True if successful, False otherwise
        """
        try:
            with connection.cursor() as cursor:
                # Check if user is the post owner
                cursor.execute("SELECT user_id FROM posts WHERE id = %s", (post_id,))
                post = cursor.fetchone()

                if not post or post['user_id'] != user_id:
                    return False

                # Delete related data (cascade should handle this, but being explicit)
                cursor.execute("DELETE FROM post_photos WHERE post_id = %s", (post_id,))
                cursor.execute("DELETE FROM post_videos WHERE post_id = %s", (post_id,))
                cursor.execute("DELETE FROM post_reactions WHERE post_id = %s", (post_id,))
                cursor.execute("DELETE FROM donators WHERE post_id = %s", (post_id,))
                cursor.execute("DELETE FROM supporters WHERE post_id = %s", (post_id,))
                cursor.execute("DELETE FROM comments WHERE post_id = %s", (post_id,))

                # Delete post
                cursor.execute("DELETE FROM posts WHERE id = %s", (post_id,))

                connection.commit()
                return True
        except Exception as e:
            connection.rollback()
            print(f"Error deleting post: {e}")
            return False

    @staticmethod
    def create_comment(connection, post_id, user_id, content, parent_id=None):
        """
        Create a comment on a post

        Args:
            connection: Database connection
            post_id: Post's ID
            user_id: User's ID
            content: Comment content
            parent_id: Parent comment ID for replies (optional)

        Returns:
            int: Comment ID if successful, None otherwise
        """
        try:
            with connection.cursor() as cursor:
                sql = """
                    INSERT INTO comments (post_id, user_id, content, parent_id, status)
                    VALUES (%s, %s, %s, %s, 'visible')
                """
                cursor.execute(sql, (post_id, user_id, content, parent_id))
                connection.commit()
                return cursor.lastrowid
        except Exception as e:
            connection.rollback()
            print(f"Error creating comment: {e}")
            return None

    @staticmethod
    def get_comments(connection, post_id, status='visible', limit=50, offset=0):
        """
        Get comments for a post

        Args:
            connection: Database connection
            post_id: Post's ID
            status: Filter by status (default: 'visible')
            limit: Number of comments to return
            offset: Offset for pagination

        Returns:
            list: List of comments with user info or empty list
        """
        try:
            with connection.cursor() as cursor:
                sql = """
                    SELECT
                        c.*,
                        u.first_name, u.last_name, u.profile_image,
                        COUNT(DISTINCT replies.id) as reply_count
                    FROM comments c
                    LEFT JOIN users u ON c.user_id = u.id
                    LEFT JOIN comments replies ON replies.parent_id = c.id AND replies.status = 'visible'
                    WHERE c.post_id = %s AND c.status = %s AND c.parent_id IS NULL
                    GROUP BY c.id
                    ORDER BY c.created_at DESC
                    LIMIT %s OFFSET %s
                """
                cursor.execute(sql, (post_id, status, limit, offset))
                comments = cursor.fetchall()

                # Get replies for each comment
                for comment in comments:
                    cursor.execute("""
                        SELECT
                            c.*,
                            u.first_name, u.last_name, u.profile_image
                        FROM comments c
                        LEFT JOIN users u ON c.user_id = u.id
                        WHERE c.parent_id = %s AND c.status = 'visible'
                        ORDER BY c.created_at ASC
                    """, (comment['id'],))
                    comment['replies'] = cursor.fetchall()

                return comments
        except Exception as e:
            print(f"Error fetching comments: {e}")
            return []

    @staticmethod
    def get_comment_by_id(connection, comment_id):
        """
        Get a single comment by ID

        Args:
            connection: Database connection
            comment_id: Comment's ID

        Returns:
            dict: Comment data with user info or None if not found
        """
        try:
            with connection.cursor() as cursor:
                sql = """
                    SELECT
                        c.*,
                        u.first_name, u.last_name, u.profile_image
                    FROM comments c
                    LEFT JOIN users u ON c.user_id = u.id
                    WHERE c.id = %s
                """
                cursor.execute(sql, (comment_id,))
                return cursor.fetchone()
        except Exception as e:
            print(f"Error fetching comment: {e}")
            return None

    @staticmethod
    def update_comment(connection, comment_id, user_id, content):
        """
        Update a comment (only by owner)

        Args:
            connection: Database connection
            comment_id: Comment's ID
            user_id: User's ID (must be comment owner)
            content: New comment content

        Returns:
            bool: True if successful, False otherwise
        """
        try:
            with connection.cursor() as cursor:
                # Check if user is the comment owner
                cursor.execute("SELECT user_id FROM comments WHERE id = %s", (comment_id,))
                comment = cursor.fetchone()

                if not comment or comment['user_id'] != user_id:
                    return False

                # Update comment
                sql = "UPDATE comments SET content = %s WHERE id = %s"
                cursor.execute(sql, (content, comment_id))
                connection.commit()
                return True
        except Exception as e:
            connection.rollback()
            print(f"Error updating comment: {e}")
            return False

    @staticmethod
    def delete_comment(connection, comment_id, user_id):
        """
        Delete a comment (soft delete by updating status to 'deleted')

        Args:
            connection: Database connection
            comment_id: Comment's ID
            user_id: User's ID (must be comment owner)

        Returns:
            bool: True if successful, False otherwise
        """
        try:
            with connection.cursor() as cursor:
                # Check if user is the comment owner
                cursor.execute("SELECT user_id FROM comments WHERE id = %s", (comment_id,))
                comment = cursor.fetchone()

                if not comment or comment['user_id'] != user_id:
                    return False

                # Soft delete by updating status
                sql = "UPDATE comments SET status = 'deleted', content = '[deleted]' WHERE id = %s"
                cursor.execute(sql, (comment_id,))
                connection.commit()
                return True
        except Exception as e:
            connection.rollback()
            print(f"Error deleting comment: {e}")
            return False

    @staticmethod
    def hide_comment(connection, comment_id):
        """
        Hide a comment (admin function - updates status to 'hidden')

        Args:
            connection: Database connection
            comment_id: Comment's ID

        Returns:
            bool: True if successful, False otherwise
        """
        try:
            with connection.cursor() as cursor:
                sql = "UPDATE comments SET status = 'hidden' WHERE id = %s"
                cursor.execute(sql, (comment_id,))
                connection.commit()
                return True
        except Exception as e:
            connection.rollback()
            print(f"Error hiding comment: {e}")
            return False

    @staticmethod
    def get_post_reactions(connection, post_id):
        """
        Get all reactions for a post with user details

        Args:
            connection: Database connection
            post_id: Post's ID

        Returns:
            list: List of reactions with user info or empty list
        """
        try:
            with connection.cursor() as cursor:
                sql = """
                    SELECT
                        pr.id, pr.reaction_type, pr.created_at,
                        u.id as user_id, u.first_name, u.last_name, u.profile_image
                    FROM post_reactions pr
                    LEFT JOIN users u ON pr.user_id = u.id
                    WHERE pr.post_id = %s
                    ORDER BY pr.created_at DESC
                """
                cursor.execute(sql, (post_id,))
                return cursor.fetchall()
        except Exception as e:
            print(f"Error fetching reactions: {e}")
            return []

    @staticmethod
    def get_post_donators(connection, post_id):
        """
        Get all donators for a post with user details

        Args:
            connection: Database connection
            post_id: Post's ID

        Returns:
            list: List of donators with user info or empty list
        """
        try:
            with connection.cursor() as cursor:
                sql = """
                    SELECT
                        d.id, d.amount, d.verification_status, d.message, d.created_at, d.updated_at,
                        u.id as user_id, u.first_name, u.last_name, u.profile_image
                    FROM donators d
                    LEFT JOIN users u ON d.user_id = u.id
                    WHERE d.post_id = %s
                    ORDER BY d.created_at DESC
                """
                cursor.execute(sql, (post_id,))
                return cursor.fetchall()
        except Exception as e:
            print(f"Error fetching donators: {e}")
            return []

    @staticmethod
    def get_post_supporters(connection, post_id):
        """
        Get all supporters for a post with user details

        Args:
            connection: Database connection
            post_id: Post's ID

        Returns:
            list: List of supporters with user info or empty list
        """
        try:
            with connection.cursor() as cursor:
                sql = """
                    SELECT
                        s.id, s.support_type, s.message, s.created_at,
                        u.id as user_id, u.first_name, u.last_name, u.profile_image
                    FROM supporters s
                    LEFT JOIN users u ON s.user_id = u.id
                    WHERE s.post_id = %s
                    ORDER BY s.created_at DESC
                """
                cursor.execute(sql, (post_id,))
                return cursor.fetchall()
        except Exception as e:
            print(f"Error fetching supporters: {e}")
            return []

    @staticmethod
    def get_donator_by_id(connection, donator_id):
        """
        Get a single donator by ID with user details and proofs

        Args:
            connection: Database connection
            donator_id: Donator's ID

        Returns:
            dict: Donator data with user info and proofs or None if not found
        """
        try:
            with connection.cursor() as cursor:
                # Get donator with user info
                sql = """
                    SELECT
                        d.*,
                        u.first_name, u.last_name, u.profile_image,
                        p.title as post_title, p.post_type
                    FROM donators d
                    LEFT JOIN users u ON d.user_id = u.id
                    LEFT JOIN posts p ON d.post_id = p.id
                    WHERE d.id = %s
                """
                cursor.execute(sql, (donator_id,))
                donator = cursor.fetchone()

                if not donator:
                    return None

                # Get proof images
                cursor.execute(
                    "SELECT id, image_url, created_at FROM donator_proofs WHERE donator_id = %s ORDER BY created_at",
                    (donator_id,)
                )
                donator['proofs'] = cursor.fetchall()

                return donator
        except Exception as e:
            print(f"Error fetching donator: {e}")
            return None

    @staticmethod
    def get_all_donators(connection, filters=None, limit=50, offset=0):
        """
        Get all donators with optional filters

        Args:
            connection: Database connection
            filters: Dictionary with optional filters
                - user_id: Filter by user
                - post_id: Filter by post
                - verification_status: Filter by status
            limit: Number of donators to return
            offset: Offset for pagination

        Returns:
            list: List of donators or empty list
        """
        try:
            with connection.cursor() as cursor:
                # Build query with filters
                where_clauses = []
                params = []

                if filters:
                    if filters.get('user_id'):
                        where_clauses.append("d.user_id = %s")
                        params.append(filters['user_id'])
                    if filters.get('post_id'):
                        where_clauses.append("d.post_id = %s")
                        params.append(filters['post_id'])
                    if filters.get('verification_status'):
                        where_clauses.append("d.verification_status = %s")
                        params.append(filters['verification_status'])

                where_sql = "WHERE " + " AND ".join(where_clauses) if where_clauses else ""

                sql = f"""
                    SELECT
                        d.*,
                        u.first_name, u.last_name, u.profile_image,
                        p.title as post_title, p.post_type
                    FROM donators d
                    LEFT JOIN users u ON d.user_id = u.id
                    LEFT JOIN posts p ON d.post_id = p.id
                    {where_sql}
                    ORDER BY d.created_at DESC
                    LIMIT %s OFFSET %s
                """
                params.extend([limit, offset])
                cursor.execute(sql, tuple(params))
                donators = cursor.fetchall()

                # Get proofs for each donator
                for donator in donators:
                    cursor.execute(
                        "SELECT id, image_url, created_at FROM donator_proofs WHERE donator_id = %s ORDER BY created_at",
                        (donator['id'],)
                    )
                    donator['proofs'] = cursor.fetchall()

                return donators
        except Exception as e:
            print(f"Error fetching donators: {e}")
            return []

    @staticmethod
    def update_donator(connection, donator_id, user_id, update_data):
        """
        Update donator information (only by owner or for verification status)

        Args:
            connection: Database connection
            donator_id: Donator's ID
            user_id: User's ID (must be donator owner for most fields)
            update_data: Dictionary containing fields to update

        Returns:
            bool: True if successful, False otherwise
        """
        try:
            if not update_data:
                return False

            with connection.cursor() as cursor:
                # Check if user is the donator owner
                cursor.execute("SELECT user_id FROM donators WHERE id = %s", (donator_id,))
                donator = cursor.fetchone()

                if not donator:
                    return False

                # Allow owner to update message and amount
                # Allow post owner to update verification_status (add this logic later if needed)
                if donator['user_id'] != user_id:
                    return False

                # Build dynamic SQL query
                allowed_fields = ['amount', 'verification_status', 'message']
                set_clauses = []
                values = []

                for key, value in update_data.items():
                    if key in allowed_fields:
                        set_clauses.append(f"{key} = %s")
                        values.append(value)

                if not set_clauses:
                    return False

                values.append(donator_id)
                sql = f"UPDATE donators SET {', '.join(set_clauses)} WHERE id = %s"
                cursor.execute(sql, tuple(values))
                connection.commit()
                return True
        except Exception as e:
            connection.rollback()
            print(f"Error updating donator: {e}")
            return False

    @staticmethod
    def add_donator_proof(connection, donator_id, image_url):
        """
        Add a proof image to a donator

        Args:
            connection: Database connection
            donator_id: Donator's ID
            image_url: URL/path of the proof image

        Returns:
            int: Proof ID if successful, None otherwise
        """
        try:
            with connection.cursor() as cursor:
                sql = "INSERT INTO donator_proofs (donator_id, image_url) VALUES (%s, %s)"
                cursor.execute(sql, (donator_id, image_url))
                connection.commit()
                return cursor.lastrowid
        except Exception as e:
            connection.rollback()
            print(f"Error adding donator proof: {e}")
            return None

    @staticmethod
    def get_supporter_by_id(connection, supporter_id):
        """
        Get a single supporter by ID with user details and proofs

        Args:
            connection: Database connection
            supporter_id: Supporter's ID

        Returns:
            dict: Supporter data with user info and proofs or None if not found
        """
        try:
            with connection.cursor() as cursor:
                # Get supporter with user info
                sql = """
                    SELECT
                        s.*,
                        u.first_name, u.last_name, u.profile_image,
                        p.title as post_title, p.post_type
                    FROM supporters s
                    LEFT JOIN users u ON s.user_id = u.id
                    LEFT JOIN posts p ON s.post_id = p.id
                    WHERE s.id = %s
                """
                cursor.execute(sql, (supporter_id,))
                supporter = cursor.fetchone()

                if not supporter:
                    return None

                # Get proof images
                cursor.execute(
                    "SELECT id, image_url, created_at FROM supporter_proofs WHERE supporter_id = %s ORDER BY created_at",
                    (supporter_id,)
                )
                supporter['proofs'] = cursor.fetchall()

                return supporter
        except Exception as e:
            print(f"Error fetching supporter: {e}")
            return None

    @staticmethod
    def get_all_supporters(connection, filters=None, limit=50, offset=0):
        """
        Get all supporters with optional filters

        Args:
            connection: Database connection
            filters: Dictionary with optional filters
                - user_id: Filter by user
                - post_id: Filter by post
                - support_type: Filter by support type
            limit: Number of supporters to return
            offset: Offset for pagination

        Returns:
            list: List of supporters or empty list
        """
        try:
            with connection.cursor() as cursor:
                # Build query with filters
                where_clauses = []
                params = []

                if filters:
                    if filters.get('user_id'):
                        where_clauses.append("s.user_id = %s")
                        params.append(filters['user_id'])
                    if filters.get('post_id'):
                        where_clauses.append("s.post_id = %s")
                        params.append(filters['post_id'])
                    if filters.get('support_type'):
                        where_clauses.append("s.support_type = %s")
                        params.append(filters['support_type'])

                where_sql = "WHERE " + " AND ".join(where_clauses) if where_clauses else ""

                sql = f"""
                    SELECT
                        s.*,
                        u.first_name, u.last_name, u.profile_image,
                        p.title as post_title, p.post_type
                    FROM supporters s
                    LEFT JOIN users u ON s.user_id = u.id
                    LEFT JOIN posts p ON s.post_id = p.id
                    {where_sql}
                    ORDER BY s.created_at DESC
                    LIMIT %s OFFSET %s
                """
                params.extend([limit, offset])
                cursor.execute(sql, tuple(params))
                supporters = cursor.fetchall()

                # Get proofs for each supporter
                for supporter in supporters:
                    cursor.execute(
                        "SELECT id, image_url, created_at FROM supporter_proofs WHERE supporter_id = %s ORDER BY created_at",
                        (supporter['id'],)
                    )
                    supporter['proofs'] = cursor.fetchall()

                return supporters
        except Exception as e:
            print(f"Error fetching supporters: {e}")
            return []

    @staticmethod
    def update_supporter(connection, supporter_id, user_id, update_data):
        """
        Update supporter information (only by owner)

        Args:
            connection: Database connection
            supporter_id: Supporter's ID
            user_id: User's ID (must be supporter owner)
            update_data: Dictionary containing fields to update

        Returns:
            bool: True if successful, False otherwise
        """
        try:
            if not update_data:
                return False

            with connection.cursor() as cursor:
                # Check if user is the supporter owner
                cursor.execute("SELECT user_id FROM supporters WHERE id = %s", (supporter_id,))
                supporter = cursor.fetchone()

                if not supporter or supporter['user_id'] != user_id:
                    return False

                # Build dynamic SQL query
                allowed_fields = ['support_type', 'message']
                set_clauses = []
                values = []

                for key, value in update_data.items():
                    if key in allowed_fields:
                        set_clauses.append(f"{key} = %s")
                        values.append(value)

                if not set_clauses:
                    return False

                values.append(supporter_id)
                sql = f"UPDATE supporters SET {', '.join(set_clauses)} WHERE id = %s"
                cursor.execute(sql, tuple(values))
                connection.commit()
                return True
        except Exception as e:
            connection.rollback()
            print(f"Error updating supporter: {e}")
            return False

    @staticmethod
    def add_supporter_proof(connection, supporter_id, image_url):
        """
        Add a proof image to a supporter

        Args:
            connection: Database connection
            supporter_id: Supporter's ID
            image_url: URL/path of the proof image

        Returns:
            int: Proof ID if successful, None otherwise
        """
        try:
            with connection.cursor() as cursor:
                sql = "INSERT INTO supporter_proofs (supporter_id, image_url) VALUES (%s, %s)"
                cursor.execute(sql, (supporter_id, image_url))
                connection.commit()
                return cursor.lastrowid
        except Exception as e:
            connection.rollback()
            print(f"Error adding supporter proof: {e}")
            return None

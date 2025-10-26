import pymysql
from datetime import datetime

class AdminModel:
    """Admin model for administrative operations"""

    # ==================== USER MANAGEMENT ====================

    @staticmethod
    def get_all_users(connection, limit=50, offset=0, account_type=None, badge=None):
        """
        Get all users with optional filtering

        Args:
            connection: Database connection
            limit: Number of records to return
            offset: Number of records to skip
            account_type: Filter by account type
            badge: Filter by badge status

        Returns:
            dict: Users list and total count
        """
        try:
            with connection.cursor() as cursor:
                # Build WHERE clause
                where_clauses = []
                params = []

                if account_type:
                    where_clauses.append("account_type = %s")
                    params.append(account_type)

                if badge:
                    where_clauses.append("badge = %s")
                    params.append(badge)

                where_sql = f"WHERE {' AND '.join(where_clauses)}" if where_clauses else ""

                # Get total count
                count_sql = f"SELECT COUNT(*) as total FROM users {where_sql}"
                cursor.execute(count_sql, tuple(params))
                total = cursor.fetchone()['total']

                # Get users
                params.extend([limit, offset])
                sql = f"""
                    SELECT id, first_name, last_name, email, address, age, number,
                           account_type, badge, profile_image, verification_selfie, valid_id,
                           last_logon, created_at, updated_at
                    FROM users
                    {where_sql}
                    ORDER BY created_at DESC
                    LIMIT %s OFFSET %s
                """
                cursor.execute(sql, tuple(params))
                users = cursor.fetchall()

                return {
                    'users': users,
                    'total': total,
                    'limit': limit,
                    'offset': offset
                }
        except Exception as e:
            print(f"Error fetching users: {e}")
            return None

    @staticmethod
    def get_verification_requests(connection, limit=50, offset=0):
        """
        Get users with pending verification (under_review badge)

        Args:
            connection: Database connection
            limit: Number of records to return
            offset: Number of records to skip

        Returns:
            dict: Users list and total count
        """
        try:
            with connection.cursor() as cursor:
                # Get total count
                cursor.execute("SELECT COUNT(*) as total FROM users WHERE badge = 'under_review'")
                total = cursor.fetchone()['total']

                # Get users
                sql = """
                    SELECT id, first_name, last_name, email, address, age, number,
                           account_type, badge, profile_image, verification_selfie, valid_id,
                           created_at
                    FROM users
                    WHERE badge = 'under_review'
                    ORDER BY created_at ASC
                    LIMIT %s OFFSET %s
                """
                cursor.execute(sql, (limit, offset))
                users = cursor.fetchall()

                return {
                    'users': users,
                    'total': total,
                    'limit': limit,
                    'offset': offset
                }
        except Exception as e:
            print(f"Error fetching verification requests: {e}")
            return None

    @staticmethod
    def update_user_badge(connection, user_id, badge):
        """
        Update user's verification badge

        Args:
            connection: Database connection
            user_id: User's ID
            badge: New badge status ('verified' or 'under_review')

        Returns:
            bool: True if successful, False otherwise
        """
        try:
            with connection.cursor() as cursor:
                sql = "UPDATE users SET badge = %s WHERE id = %s"
                cursor.execute(sql, (badge, user_id))
                connection.commit()
                return cursor.rowcount > 0
        except Exception as e:
            connection.rollback()
            print(f"Error updating user badge: {e}")
            return False

    @staticmethod
    def update_user_account_type(connection, user_id, account_type):
        """
        Update user's account type

        Args:
            connection: Database connection
            user_id: User's ID
            account_type: New account type

        Returns:
            bool: True if successful, False otherwise
        """
        try:
            with connection.cursor() as cursor:
                sql = "UPDATE users SET account_type = %s WHERE id = %s"
                cursor.execute(sql, (account_type, user_id))
                connection.commit()
                return cursor.rowcount > 0
        except Exception as e:
            connection.rollback()
            print(f"Error updating user account type: {e}")
            return False

    # ==================== POST MANAGEMENT ====================

    @staticmethod
    def get_all_posts(connection, limit=50, offset=0, post_type=None, status=None):
        """
        Get all posts with optional filtering

        Args:
            connection: Database connection
            limit: Number of records to return
            offset: Number of records to skip
            post_type: Filter by post type
            status: Filter by status

        Returns:
            dict: Posts list and total count
        """
        try:
            with connection.cursor() as cursor:
                # Build WHERE clause
                where_clauses = []
                params = []

                if post_type:
                    where_clauses.append("p.post_type = %s")
                    params.append(post_type)

                if status:
                    where_clauses.append("p.status = %s")
                    params.append(status)

                where_sql = f"WHERE {' AND '.join(where_clauses)}" if where_clauses else ""

                # Get total count
                count_sql = f"SELECT COUNT(*) as total FROM posts p {where_sql}"
                cursor.execute(count_sql, tuple(params))
                total = cursor.fetchone()['total']

                # Get posts with user info
                params.extend([limit, offset])
                sql = f"""
                    SELECT p.*,
                           u.first_name, u.last_name, u.email, u.account_type, u.badge
                    FROM posts p
                    JOIN users u ON p.user_id = u.id
                    {where_sql}
                    ORDER BY p.created_at DESC
                    LIMIT %s OFFSET %s
                """
                cursor.execute(sql, tuple(params))
                posts = cursor.fetchall()

                return {
                    'posts': posts,
                    'total': total,
                    'limit': limit,
                    'offset': offset
                }
        except Exception as e:
            print(f"Error fetching posts: {e}")
            return None

    @staticmethod
    def update_post_status(connection, post_id, status):
        """
        Update post status

        Args:
            connection: Database connection
            post_id: Post ID
            status: New status ('active', 'closed', 'pending')

        Returns:
            bool: True if successful, False otherwise
        """
        try:
            with connection.cursor() as cursor:
                sql = "UPDATE posts SET status = %s WHERE id = %s"
                cursor.execute(sql, (status, post_id))
                connection.commit()
                return cursor.rowcount > 0
        except Exception as e:
            connection.rollback()
            print(f"Error updating post status: {e}")
            return False

    # ==================== COMMENT MODERATION ====================

    @staticmethod
    def get_all_comments(connection, limit=50, offset=0, status=None):
        """
        Get all comments with optional filtering

        Args:
            connection: Database connection
            limit: Number of records to return
            offset: Number of records to skip
            status: Filter by status

        Returns:
            dict: Comments list and total count
        """
        try:
            with connection.cursor() as cursor:
                where_sql = "WHERE c.status = %s" if status else ""
                params = [status] if status else []

                # Get total count
                count_sql = f"SELECT COUNT(*) as total FROM comments c {where_sql}"
                cursor.execute(count_sql, tuple(params))
                total = cursor.fetchone()['total']

                # Get comments with user and post info
                params.extend([limit, offset])
                sql = f"""
                    SELECT c.*,
                           u.first_name, u.last_name, u.email,
                           p.title as post_title, p.post_type
                    FROM comments c
                    JOIN users u ON c.user_id = u.id
                    JOIN posts p ON c.post_id = p.id
                    {where_sql}
                    ORDER BY c.created_at DESC
                    LIMIT %s OFFSET %s
                """
                cursor.execute(sql, tuple(params))
                comments = cursor.fetchall()

                return {
                    'comments': comments,
                    'total': total,
                    'limit': limit,
                    'offset': offset
                }
        except Exception as e:
            print(f"Error fetching comments: {e}")
            return None

    @staticmethod
    def update_comment_status(connection, comment_id, status):
        """
        Update comment status (for moderation)

        Args:
            connection: Database connection
            comment_id: Comment ID
            status: New status ('visible', 'hidden', 'deleted')

        Returns:
            bool: True if successful, False otherwise
        """
        try:
            with connection.cursor() as cursor:
                sql = "UPDATE comments SET status = %s WHERE id = %s"
                cursor.execute(sql, (status, comment_id))
                connection.commit()
                return cursor.rowcount > 0
        except Exception as e:
            connection.rollback()
            print(f"Error updating comment status: {e}")
            return False

    # ==================== DONATION MANAGEMENT ====================

    @staticmethod
    def get_all_donations(connection, limit=50, offset=0, verification_status=None):
        """
        Get all donations with optional filtering

        Args:
            connection: Database connection
            limit: Number of records to return
            offset: Number of records to skip
            verification_status: Filter by verification status

        Returns:
            dict: Donations list and total count
        """
        try:
            with connection.cursor() as cursor:
                where_sql = "WHERE d.verification_status = %s" if verification_status else ""
                params = [verification_status] if verification_status else []

                # Get total count
                count_sql = f"SELECT COUNT(*) as total FROM donators d {where_sql}"
                cursor.execute(count_sql, tuple(params))
                total = cursor.fetchone()['total']

                # Get donations with user and post info
                params.extend([limit, offset])
                sql = f"""
                    SELECT d.*,
                           u.first_name, u.last_name, u.email,
                           p.title as post_title, p.post_type
                    FROM donators d
                    JOIN users u ON d.user_id = u.id
                    JOIN posts p ON d.post_id = p.id
                    {where_sql}
                    ORDER BY d.created_at DESC
                    LIMIT %s OFFSET %s
                """
                cursor.execute(sql, tuple(params))
                donations = cursor.fetchall()

                # Get proof images for each donation
                for donation in donations:
                    cursor.execute(
                        "SELECT image_url FROM donator_proofs WHERE donator_id = %s",
                        (donation['id'],)
                    )
                    donation['proofs'] = cursor.fetchall()

                return {
                    'donations': donations,
                    'total': total,
                    'limit': limit,
                    'offset': offset
                }
        except Exception as e:
            print(f"Error fetching donations: {e}")
            return None

    @staticmethod
    def update_donation_status(connection, donation_id, verification_status):
        """
        Update donation verification status

        Args:
            connection: Database connection
            donation_id: Donation ID
            verification_status: New status ('pending', 'ongoing', 'fulfilled')

        Returns:
            bool: True if successful, False otherwise
        """
        try:
            with connection.cursor() as cursor:
                sql = "UPDATE donators SET verification_status = %s WHERE id = %s"
                cursor.execute(sql, (verification_status, donation_id))
                connection.commit()
                return cursor.rowcount > 0
        except Exception as e:
            connection.rollback()
            print(f"Error updating donation status: {e}")
            return False

    # ==================== SUPPORTER MANAGEMENT ====================

    @staticmethod
    def get_all_supporters(connection, limit=50, offset=0):
        """
        Get all supporters

        Args:
            connection: Database connection
            limit: Number of records to return
            offset: Number of records to skip

        Returns:
            dict: Supporters list and total count
        """
        try:
            with connection.cursor() as cursor:
                # Get total count
                cursor.execute("SELECT COUNT(*) as total FROM supporters")
                total = cursor.fetchone()['total']

                # Get supporters with user and post info
                sql = """
                    SELECT s.*,
                           u.first_name, u.last_name, u.email,
                           p.title as post_title, p.post_type
                    FROM supporters s
                    JOIN users u ON s.user_id = u.id
                    JOIN posts p ON s.post_id = p.id
                    ORDER BY s.created_at DESC
                    LIMIT %s OFFSET %s
                """
                cursor.execute(sql, (limit, offset))
                supporters = cursor.fetchall()

                # Get proof images for each supporter
                for supporter in supporters:
                    cursor.execute(
                        "SELECT image_url FROM supporter_proofs WHERE supporter_id = %s",
                        (supporter['id'],)
                    )
                    supporter['proofs'] = cursor.fetchall()

                return {
                    'supporters': supporters,
                    'total': total,
                    'limit': limit,
                    'offset': offset
                }
        except Exception as e:
            print(f"Error fetching supporters: {e}")
            return None

    # ==================== STATISTICS ====================

    @staticmethod
    def get_statistics(connection):
        """
        Get platform statistics

        Args:
            connection: Database connection

        Returns:
            dict: Various platform statistics
        """
        try:
            with connection.cursor() as cursor:
                stats = {}

                # User statistics
                cursor.execute("""
                    SELECT
                        COUNT(*) as total_users,
                        SUM(CASE WHEN account_type = 'beneficiary' THEN 1 ELSE 0 END) as beneficiaries,
                        SUM(CASE WHEN account_type = 'donor' THEN 1 ELSE 0 END) as donors,
                        SUM(CASE WHEN account_type = 'volunteer' THEN 1 ELSE 0 END) as volunteers,
                        SUM(CASE WHEN account_type = 'verified_organization' THEN 1 ELSE 0 END) as organizations,
                        SUM(CASE WHEN badge = 'verified' THEN 1 ELSE 0 END) as verified_users,
                        SUM(CASE WHEN badge = 'under_review' THEN 1 ELSE 0 END) as pending_verification
                    FROM users
                """)
                stats['users'] = cursor.fetchone()

                # Post statistics
                cursor.execute("""
                    SELECT
                        COUNT(*) as total_posts,
                        SUM(CASE WHEN post_type = 'donation' THEN 1 ELSE 0 END) as donation_posts,
                        SUM(CASE WHEN post_type = 'request' THEN 1 ELSE 0 END) as request_posts,
                        SUM(CASE WHEN status = 'active' THEN 1 ELSE 0 END) as active_posts,
                        SUM(CASE WHEN status = 'closed' THEN 1 ELSE 0 END) as closed_posts,
                        SUM(CASE WHEN status = 'pending' THEN 1 ELSE 0 END) as pending_posts
                    FROM posts
                """)
                stats['posts'] = cursor.fetchone()

                # Donation statistics
                cursor.execute("""
                    SELECT
                        COUNT(*) as total_donations,
                        SUM(amount) as total_amount,
                        AVG(amount) as average_amount,
                        SUM(CASE WHEN verification_status = 'pending' THEN 1 ELSE 0 END) as pending_donations,
                        SUM(CASE WHEN verification_status = 'ongoing' THEN 1 ELSE 0 END) as ongoing_donations,
                        SUM(CASE WHEN verification_status = 'fulfilled' THEN 1 ELSE 0 END) as fulfilled_donations
                    FROM donators
                """)
                stats['donations'] = cursor.fetchone()

                # Support statistics
                cursor.execute("""
                    SELECT
                        COUNT(*) as total_supporters,
                        SUM(CASE WHEN support_type = 'share' THEN 1 ELSE 0 END) as shares,
                        SUM(CASE WHEN support_type = 'volunteer' THEN 1 ELSE 0 END) as volunteers,
                        SUM(CASE WHEN support_type = 'advocate' THEN 1 ELSE 0 END) as advocates,
                        SUM(CASE WHEN support_type = 'other' THEN 1 ELSE 0 END) as others
                    FROM supporters
                """)
                stats['supporters'] = cursor.fetchone()

                # Comment statistics
                cursor.execute("""
                    SELECT
                        COUNT(*) as total_comments,
                        SUM(CASE WHEN status = 'visible' THEN 1 ELSE 0 END) as visible_comments,
                        SUM(CASE WHEN status = 'hidden' THEN 1 ELSE 0 END) as hidden_comments,
                        SUM(CASE WHEN status = 'deleted' THEN 1 ELSE 0 END) as deleted_comments
                    FROM comments
                """)
                stats['comments'] = cursor.fetchone()

                # Chat statistics
                cursor.execute("""
                    SELECT
                        COUNT(*) as total_chats,
                        SUM(CASE WHEN type = 'private' THEN 1 ELSE 0 END) as private_chats,
                        SUM(CASE WHEN type = 'group' THEN 1 ELSE 0 END) as group_chats
                    FROM chats
                """)
                stats['chats'] = cursor.fetchone()

                cursor.execute("SELECT COUNT(*) as total_messages FROM messages")
                stats['messages'] = cursor.fetchone()

                return stats
        except Exception as e:
            print(f"Error fetching statistics: {e}")
            return None

    # ==================== RECENT ACTIVITY ====================

    @staticmethod
    def get_recent_activity(connection, limit=20):
        """
        Get recent platform activity

        Args:
            connection: Database connection
            limit: Number of activities to return

        Returns:
            list: Recent activities
        """
        try:
            with connection.cursor() as cursor:
                activities = []

                # Recent users
                cursor.execute("""
                    SELECT 'user_registered' as activity_type,
                           id, first_name, last_name, email, created_at as activity_time
                    FROM users
                    ORDER BY created_at DESC
                    LIMIT %s
                """, (limit,))
                user_activities = cursor.fetchall()
                for activity in user_activities:
                    activity['description'] = f"{activity['first_name']} {activity['last_name']} registered"
                activities.extend(user_activities)

                # Recent posts
                cursor.execute("""
                    SELECT 'post_created' as activity_type,
                           p.id, p.title, p.post_type, p.created_at as activity_time,
                           u.first_name, u.last_name
                    FROM posts p
                    JOIN users u ON p.user_id = u.id
                    ORDER BY p.created_at DESC
                    LIMIT %s
                """, (limit,))
                post_activities = cursor.fetchall()
                for activity in post_activities:
                    activity['description'] = f"{activity['first_name']} {activity['last_name']} created {activity['post_type']} post: {activity['title']}"
                activities.extend(post_activities)

                # Recent donations
                cursor.execute("""
                    SELECT 'donation_made' as activity_type,
                           d.id, d.amount, d.created_at as activity_time,
                           u.first_name, u.last_name,
                           p.title as post_title
                    FROM donators d
                    JOIN users u ON d.user_id = u.id
                    JOIN posts p ON d.post_id = p.id
                    ORDER BY d.created_at DESC
                    LIMIT %s
                """, (limit,))
                donation_activities = cursor.fetchall()
                for activity in donation_activities:
                    activity['description'] = f"{activity['first_name']} {activity['last_name']} donated to: {activity['post_title']}"
                activities.extend(donation_activities)

                # Sort all activities by time
                activities.sort(key=lambda x: x['activity_time'], reverse=True)

                return activities[:limit]
        except Exception as e:
            print(f"Error fetching recent activity: {e}")
            return None

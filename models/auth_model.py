import bcrypt
import pymysql
from datetime import datetime

class AuthModel:
    """Authentication model for user operations"""

    @staticmethod
    def hash_password(password):
        """Hash a password using bcrypt"""
        salt = bcrypt.gensalt()
        hashed = bcrypt.hashpw(password.encode('utf-8'), salt)
        return hashed.decode('utf-8')

    @staticmethod
    def verify_password(password, hashed_password):
        """Verify a password against its hash"""
        return bcrypt.checkpw(
            password.encode('utf-8'),
            hashed_password.encode('utf-8')
        )

    @staticmethod
    def create_user(connection, user_data):
        """
        Create a new user in the database

        Args:
            connection: Database connection
            user_data: Dictionary containing user information

        Returns:
            int: User ID if successful, None otherwise
        """
        try:
            with connection.cursor() as cursor:
                sql = """
                    INSERT INTO users (
                        first_name, last_name, email, password_hash, address,
                        age, number, account_type, badge,
                        profile_image, verification_selfie, valid_id
                    ) VALUES (
                        %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
                    )
                """
                cursor.execute(sql, (
                    user_data.get('first_name'),
                    user_data.get('last_name'),
                    user_data.get('email'),
                    user_data.get('password_hash'),
                    user_data.get('address'),
                    user_data.get('age'),
                    user_data.get('number'),
                    user_data.get('account_type', 'beneficiary'),
                    user_data.get('badge', 'under_review'),
                    user_data.get('profile_image'),
                    user_data.get('verification_selfie'),
                    user_data.get('valid_id')
                ))
                connection.commit()
                return cursor.lastrowid
        except pymysql.IntegrityError as e:
            connection.rollback()
            print(f"Integrity error creating user: {e}")
            return None
        except Exception as e:
            connection.rollback()
            print(f"Error creating user: {e}")
            return None

    @staticmethod
    def get_user_by_email(connection, email):
        """
        Get user by email

        Args:
            connection: Database connection
            email: User's email

        Returns:
            dict: User data or None if not found
        """
        try:
            with connection.cursor() as cursor:
                sql = "SELECT * FROM users WHERE email = %s"
                cursor.execute(sql, (email,))
                return cursor.fetchone()
        except Exception as e:
            print(f"Error fetching user: {e}")
            return None

    @staticmethod
    def update_last_logon(connection, user_id):
        """
        Update user's last logon timestamp

        Args:
            connection: Database connection
            user_id: User's ID

        Returns:
            bool: True if successful, False otherwise
        """
        try:
            with connection.cursor() as cursor:
                sql = "UPDATE users SET last_logon = %s WHERE id = %s"
                cursor.execute(sql, (datetime.now(), user_id))
                connection.commit()
                return True
        except Exception as e:
            connection.rollback()
            print(f"Error updating last logon: {e}")
            return False

    @staticmethod
    def get_user_by_id(connection, user_id):
        """
        Get user by ID

        Args:
            connection: Database connection
            user_id: User's ID

        Returns:
            dict: User data or None if not found
        """
        try:
            with connection.cursor() as cursor:
                sql = "SELECT * FROM users WHERE id = %s"
                cursor.execute(sql, (user_id,))
                return cursor.fetchone()
        except Exception as e:
            print(f"Error fetching user: {e}")
            return None

    @staticmethod
    def update_user(connection, user_id, update_data):
        """
        Update user information

        Args:
            connection: Database connection
            user_id: User's ID
            update_data: Dictionary containing fields to update

        Returns:
            bool: True if successful, False otherwise
        """
        try:
            if not update_data:
                return False

            # Build dynamic SQL query based on fields to update
            set_clauses = []
            values = []
            for key, value in update_data.items():
                set_clauses.append(f"{key} = %s")
                values.append(value)

            # Add user_id to the end of values
            values.append(user_id)

            with connection.cursor() as cursor:
                sql = f"UPDATE users SET {', '.join(set_clauses)} WHERE id = %s"
                cursor.execute(sql, tuple(values))
                connection.commit()
                return True
        except Exception as e:
            connection.rollback()
            print(f"Error updating user: {e}")
            return False

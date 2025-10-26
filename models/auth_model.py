import bcrypt
import pymysql
import random
import string
from datetime import datetime, timedelta

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

    # ==================== OTP MANAGEMENT ====================

    @staticmethod
    def generate_otp(length=6):
        """
        Generate a random OTP code

        Args:
            length: Length of OTP code (default: 6)

        Returns:
            str: OTP code
        """
        return ''.join(random.choices(string.digits, k=length))

    @staticmethod
    def create_otp(connection, user_id, otp_type='password_reset', validity_minutes=3):
        """
        Create a new OTP for a user

        Args:
            connection: Database connection
            user_id: User's ID
            otp_type: Type of OTP ('email_verification', 'password_reset', 'login')
            validity_minutes: How long the OTP is valid (default: 3 minutes)

        Returns:
            str: OTP code if successful, None otherwise
        """
        try:
            # Generate OTP
            otp_code = AuthModel.generate_otp()

            # Invalidate any existing active OTPs of the same type for this user
            with connection.cursor() as cursor:
                invalidate_sql = """
                    UPDATE user_otps
                    SET validity = 'inactive'
                    WHERE user_id = %s AND type = %s AND validity = 'active'
                """
                cursor.execute(invalidate_sql, (user_id, otp_type))

                # Create new OTP
                expires_at = datetime.now() + timedelta(minutes=validity_minutes)
                insert_sql = """
                    INSERT INTO user_otps (
                        user_id, otp_code, type, validity, is_used, expires_at
                    ) VALUES (%s, %s, %s, 'active', 0, %s)
                """
                cursor.execute(insert_sql, (user_id, otp_code, otp_type, expires_at))
                connection.commit()

                return otp_code

        except Exception as e:
            connection.rollback()
            print(f"Error creating OTP: {e}")
            return None

    @staticmethod
    def verify_otp(connection, user_id, otp_code, otp_type='password_reset'):
        """
        Verify an OTP code

        Args:
            connection: Database connection
            user_id: User's ID
            otp_code: OTP code to verify
            otp_type: Type of OTP to verify

        Returns:
            dict: OTP record if valid, None otherwise
        """
        try:
            with connection.cursor() as cursor:
                sql = """
                    SELECT * FROM user_otps
                    WHERE user_id = %s
                    AND otp_code = %s
                    AND type = %s
                    AND validity = 'active'
                    AND is_used = 0
                    AND expires_at > NOW()
                    ORDER BY created_at DESC
                    LIMIT 1
                """
                cursor.execute(sql, (user_id, otp_code, otp_type))
                return cursor.fetchone()
        except Exception as e:
            print(f"Error verifying OTP: {e}")
            return None

    @staticmethod
    def mark_otp_as_used(connection, otp_id):
        """
        Mark an OTP as used

        Args:
            connection: Database connection
            otp_id: OTP record ID

        Returns:
            bool: True if successful, False otherwise
        """
        try:
            with connection.cursor() as cursor:
                sql = """
                    UPDATE user_otps
                    SET is_used = 1, validity = 'inactive'
                    WHERE id = %s
                """
                cursor.execute(sql, (otp_id,))
                connection.commit()
                return True
        except Exception as e:
            connection.rollback()
            print(f"Error marking OTP as used: {e}")
            return False

    @staticmethod
    def invalidate_user_otps(connection, user_id, otp_type=None):
        """
        Invalidate all active OTPs for a user

        Args:
            connection: Database connection
            user_id: User's ID
            otp_type: Optional type of OTP to invalidate (if None, invalidates all types)

        Returns:
            bool: True if successful, False otherwise
        """
        try:
            with connection.cursor() as cursor:
                if otp_type:
                    sql = """
                        UPDATE user_otps
                        SET validity = 'inactive'
                        WHERE user_id = %s AND type = %s AND validity = 'active'
                    """
                    cursor.execute(sql, (user_id, otp_type))
                else:
                    sql = """
                        UPDATE user_otps
                        SET validity = 'inactive'
                        WHERE user_id = %s AND validity = 'active'
                    """
                    cursor.execute(sql, (user_id,))
                connection.commit()
                return True
        except Exception as e:
            connection.rollback()
            print(f"Error invalidating OTPs: {e}")
            return False

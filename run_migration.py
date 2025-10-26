#!/usr/bin/env python3
"""
Script to run database migrations
"""

import pymysql
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def run_migration():
    """Run the password_hash migration"""
    try:
        # Connect to database
        connection = pymysql.connect(
            host=os.getenv('DB_HOST'),
            user=os.getenv('DB_USER'),
            password=os.getenv('DB_PASSWORD'),
            database=os.getenv('DB_NAME'),
            port=int(os.getenv('DB_PORT', 3306))
        )

        print("✅ Connected to database")
        print(f"   Host: {os.getenv('DB_HOST')}")
        print(f"   Database: {os.getenv('DB_NAME')}")
        print()

        with connection.cursor() as cursor:
            # Check if password_hash column already exists
            cursor.execute("""
                SELECT COLUMN_NAME
                FROM INFORMATION_SCHEMA.COLUMNS
                WHERE TABLE_SCHEMA = %s
                AND TABLE_NAME = 'users'
                AND COLUMN_NAME = 'password_hash'
            """, (os.getenv('DB_NAME'),))

            result = cursor.fetchone()

            if result:
                print("⚠️  password_hash column already exists!")
                print("   No migration needed.")
            else:
                print("📝 Adding password_hash column to users table...")

                # Run migration
                cursor.execute("""
                    ALTER TABLE users
                    ADD COLUMN password_hash VARCHAR(255) NOT NULL AFTER valid_id
                """)

                connection.commit()
                print("✅ Migration completed successfully!")
                print("   Added column: password_hash VARCHAR(255)")

        # Verify the column was added
        with connection.cursor() as cursor:
            cursor.execute("DESCRIBE users")
            columns = cursor.fetchall()

            print("\n📋 Current users table structure:")
            for column in columns:
                print(f"   - {column[0]}: {column[1]}")

        connection.close()
        return True

    except pymysql.Error as e:
        print(f"❌ Database error: {e}")
        return False
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

if __name__ == "__main__":
    print("="*60)
    print("Database Migration Script")
    print("="*60)
    print()

    success = run_migration()

    print()
    print("="*60)
    if success:
        print("✅ Migration completed!")
    else:
        print("❌ Migration failed!")
    print("="*60)

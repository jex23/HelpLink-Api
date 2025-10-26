import boto3
from botocore.client import Config
from flask import current_app
import uuid
from werkzeug.utils import secure_filename
import os

class R2Storage:
    """Cloudflare R2 Storage handler"""

    def __init__(self):
        self.client = None
        self.bucket_name = None

    def initialize(self, app):
        """Initialize R2 client with app configuration"""
        self.client = boto3.client(
            's3',
            endpoint_url=app.config['R2_ENDPOINT'],
            aws_access_key_id=app.config['R2_ACCESS_KEY'],
            aws_secret_access_key=app.config['R2_SECRET_KEY'],
            config=Config(signature_version='s3v4'),
            region_name='auto'
        )
        self.bucket_name = app.config['R2_BUCKET_NAME']

    def upload_file(self, file, folder='uploads'):
        """
        Upload a file to R2 storage

        Args:
            file: FileStorage object from Flask request
            folder: Folder path in the bucket (default: 'uploads')

        Returns:
            str: URL path of the uploaded file or None if failed
        """
        if not file or file.filename == '':
            return None

        try:
            # Generate unique filename
            original_filename = secure_filename(file.filename)
            file_extension = os.path.splitext(original_filename)[1]
            unique_filename = f"{uuid.uuid4()}{file_extension}"

            # Create full path
            file_path = f"{folder}/{unique_filename}"

            # Upload to R2
            self.client.upload_fileobj(
                file,
                self.bucket_name,
                file_path,
                ExtraArgs={'ContentType': file.content_type}
            )

            # Return the path stored in database
            return file_path

        except Exception as e:
            print(f"Error uploading file to R2: {e}")
            return None

    def delete_file(self, file_path):
        """
        Delete a file from R2 storage

        Args:
            file_path: Path of the file in the bucket

        Returns:
            bool: True if successful, False otherwise
        """
        try:
            self.client.delete_object(
                Bucket=self.bucket_name,
                Key=file_path
            )
            return True
        except Exception as e:
            print(f"Error deleting file from R2: {e}")
            return False

    def get_file_url(self, file_path, expiration=3600):
        """
        Generate a presigned URL for accessing a file

        Args:
            file_path: Path of the file in the bucket
            expiration: URL expiration time in seconds (default: 1 hour)

        Returns:
            str: Presigned URL or None if failed
        """
        try:
            url = self.client.generate_presigned_url(
                'get_object',
                Params={
                    'Bucket': self.bucket_name,
                    'Key': file_path
                },
                ExpiresIn=expiration
            )
            return url
        except Exception as e:
            print(f"Error generating presigned URL: {e}")
            return None

# Global instance
r2_storage = R2Storage()

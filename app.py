from flask import Flask, g
from flask_cors import CORS
import pymysql
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def create_app():
    """Application factory pattern"""
    app = Flask(__name__)
    CORS(app)

    # Configuration
    app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'your-secret-key-here')
    app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size

    # Database configuration
    app.config['DB_USER'] = os.getenv('DB_USER')
    app.config['DB_PASSWORD'] = os.getenv('DB_PASSWORD')
    app.config['DB_HOST'] = os.getenv('DB_HOST')
    app.config['DB_PORT'] = int(os.getenv('DB_PORT', 3306))
    app.config['DB_NAME'] = os.getenv('DB_NAME')

    # R2 Storage configuration
    app.config['R2_ACCESS_KEY'] = os.getenv('r2_access_key')
    app.config['R2_SECRET_KEY'] = os.getenv('r2_secret_key')
    app.config['R2_ENDPOINT'] = os.getenv('r2_endpoint')
    app.config['R2_BUCKET_NAME'] = os.getenv('r2_bucket_name')

    # Initialize R2 storage with app context
    with app.app_context():
        from utils.r2_storage import r2_storage
        r2_storage.initialize(app)

    # Register blueprints
    register_blueprints(app)

    # Register error handlers
    register_error_handlers(app)

    # Register database teardown
    @app.teardown_appcontext
    def close_db(error):
        """Close database connection at the end of request"""
        db = g.pop('db', None)
        if db is not None:
            db.close()

    # Register core routes
    @app.route('/')
    def home():
        return {
            'message': 'HelpLink API',
            'status': 'running',
            'version': '1.0',
            'endpoints': {
                'health': '/health',
                'auth': '/api/auth',
                'register': '/api/auth/register',
                'login': '/api/auth/login',
                'me': '/api/auth/me',
                'update_profile': '/api/auth/profile',
                'change_password': '/api/auth/change-password',
                'credentials': '/api/credentials',
                'ids': '/api/ids',
                'profile_image': '/api/profile-image',
                'posts': '/api/posts',
                'create_post': '/api/posts (POST)',
                'get_posts': '/api/posts (GET)',
                'get_post': '/api/posts/<id> (GET)',
                'update_post': '/api/posts/<id> (PUT)',
                'close_post': '/api/posts/<id>/close (PUT)',
                'add_reaction': '/api/posts/<id>/reaction (POST)',
                'remove_reaction': '/api/posts/<id>/reaction (DELETE)',
                'donate': '/api/posts/<id>/donate (POST)',
                'support': '/api/posts/<id>/support (POST)',
                'create_comment': '/api/posts/<id>/comments (POST)',
                'get_comments': '/api/posts/<id>/comments (GET)',
                'update_comment': '/api/posts/comments/<id> (PUT)',
                'delete_comment': '/api/posts/comments/<id> (DELETE)',
                'chats': '/api/chats',
                'create_chat': '/api/chats (POST)',
                'get_chats': '/api/chats (GET)',
                'get_chat': '/api/chats/<id> (GET)',
                'send_message': '/api/chats/<id>/messages (POST)',
                'get_messages': '/api/chats/<id>/messages (GET)',
                'mark_seen': '/api/chats/<id>/messages/seen (PUT)',
                'add_participant': '/api/chats/<id>/participants (POST)'
            }
        }

    @app.route('/health')
    def health():
        """Health check endpoint"""
        try:
            conn = get_db_connection()
            # Test query
            with conn.cursor() as cursor:
                cursor.execute("SELECT 1")
            return {
                'status': 'healthy',
                'database': 'connected',
                'r2_storage': 'configured'
            }
        except Exception as e:
            return {'status': 'unhealthy', 'error': str(e)}, 500

    return app

def register_blueprints(app):
    """Register all blueprints"""
    from routes.auth import auth_bp
    from routes.credentials import credentials_bp
    from routes.post import post_bp
    from routes.chat import chat_bp
    app.register_blueprint(auth_bp, url_prefix='/api/auth')
    app.register_blueprint(credentials_bp, url_prefix='/api')
    app.register_blueprint(post_bp, url_prefix='/api/posts')
    app.register_blueprint(chat_bp, url_prefix='/api/chats')

def register_error_handlers(app):
    """Register error handlers"""
    @app.errorhandler(404)
    def not_found(error):
        return {'error': 'Endpoint not found'}, 404

    @app.errorhandler(500)
    def internal_error(error):
        return {'error': 'Internal server error'}, 500

    @app.errorhandler(413)
    def request_entity_too_large(error):
        return {'error': 'File too large (max 16MB)'}, 413

# Database connection function
def get_db_connection():
    """
    Create and return a database connection
    Uses Flask's g object to maintain connection during request lifecycle
    """
    if 'db' not in g:
        try:
            g.db = pymysql.connect(
                host=app.config['DB_HOST'],
                user=app.config['DB_USER'],
                password=app.config['DB_PASSWORD'],
                database=app.config['DB_NAME'],
                port=app.config['DB_PORT'],
                cursorclass=pymysql.cursors.DictCursor,
                autocommit=False
            )
        except pymysql.Error as e:
            print(f"Error connecting to database: {e}")
            raise
    return g.db

# Create app instance
app = create_app()

if __name__ == '__main__':
    print("=" * 60)
    print("HelpLink API Starting...")
    print("=" * 60)
    print(f"Database: {app.config['DB_HOST']}:{app.config['DB_PORT']}/{app.config['DB_NAME']}")
    print(f"R2 Bucket: {app.config['R2_BUCKET_NAME']}")
    print(f"Max File Size: {app.config['MAX_CONTENT_LENGTH'] / 1024 / 1024}MB")
    print("=" * 60)
    print("\nAPI will be available at: http://localhost:5001")
    print("Health check: http://localhost:5001/health")
    print("\nPress CTRL+C to stop the server")
    print("=" * 60)
    app.run(debug=True, host='0.0.0.0', port=5001)

# HelpLink API - Setup Guide

## Quick Start

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Configure Environment

Your `.env` file is already configured with:
- MySQL database credentials
- Cloudflare R2 storage credentials

**Important:** Add a SECRET_KEY to your `.env` file:
```bash
echo "SECRET_KEY=$(python -c 'import secrets; print(secrets.token_hex(32))')" >> .env
```

### 3. Run Database Migration

Add the `password_hash` column to your users table:

```bash
mysql -u james23 -p -h 179.61.246.136 service_connect < migrations/add_password_hash.sql
```

Or connect directly and run:
```sql
ALTER TABLE users ADD COLUMN password_hash VARCHAR(255) NOT NULL AFTER valid_id;
```

### 4. Start the API

```bash
python app.py
```

The API will start at `http://localhost:5000`

### 5. Test the API

```bash
python test_api.py
```

## Key Improvements Made

### Application Structure
✅ **Application Factory Pattern** - Better organization and testability
✅ **Centralized Configuration** - All config in one place in `create_app()`
✅ **Blueprint Registration** - Modular route organization via `register_blueprints()`
✅ **Error Handlers** - Consistent error responses via `register_error_handlers()`

### Database Management
✅ **Flask's g object** - Request-scoped database connections
✅ **Automatic cleanup** - Database connections closed via `@app.teardown_appcontext`
✅ **No manual connection management** - No need to call `conn.close()` in routes

### R2 Storage
✅ **Centralized initialization** - R2 storage initialized once at app startup
✅ **Reusable client** - Single boto3 client shared across requests
✅ **File management** - Upload, delete, and generate presigned URLs

### Security
✅ **JWT Authentication** - Token-based auth with 30-day expiration
✅ **Bcrypt password hashing** - Secure password storage
✅ **Protected routes** - `@token_required` decorator for authentication
✅ **File validation** - Allowed file extensions check

### API Features
✅ **User registration** - With file uploads (profile, selfie, ID)
✅ **User login** - Returns JWT token
✅ **Get current user** - Protected endpoint
✅ **File URL generation** - Presigned URLs for R2 files

## API Endpoints Summary

| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| GET | `/` | No | API info |
| GET | `/health` | No | Health check |
| POST | `/api/auth/register` | No | Register new user |
| POST | `/api/auth/login` | No | Login user |
| GET | `/api/auth/me` | Yes | Get current user |
| GET | `/api/auth/file-url/<path>` | Yes | Get file URL |

## File Upload Flow

1. User submits registration form with files
2. Files are validated for allowed extensions
3. Files are uploaded to Cloudflare R2 storage
4. File paths are stored in MySQL database
5. User record is created with file references

## Connection Management

### Before (Manual Management):
```python
conn = get_db_connection()
# ... do work ...
conn.close()  # Must remember to close!
```

### After (Automatic Management):
```python
conn = get_db_connection()
# ... do work ...
# Connection automatically closed at end of request!
```

## Adding New Routes

1. Create a new blueprint in `routes/` directory
2. Register it in `app.py` in the `register_blueprints()` function:

```python
def register_blueprints(app):
    from routes.auth import auth_bp
    from routes.your_route import your_bp

    app.register_blueprint(auth_bp, url_prefix='/api/auth')
    app.register_blueprint(your_bp, url_prefix='/api/your_route')
```

## Environment Variables

Required in `.env`:
```
# Database
DB_USER=your_db_user
DB_PASSWORD=your_db_password
DB_HOST=your_db_host
DB_PORT=3306
DB_NAME=your_db_name

# R2 Storage
r2_access_key=your_r2_access_key
r2_secret_key=your_r2_secret_key
r2_endpoint=your_r2_endpoint
r2_bucket_name=your_bucket_name

# Application
SECRET_KEY=your_secret_key_here
```

## Troubleshooting

### Database Connection Error
- Check database credentials in `.env`
- Verify database server is accessible
- Ensure `service_connect` database exists
- Run the migration to add `password_hash` column

### R2 Storage Error
- Verify R2 credentials in `.env`
- Check R2 bucket exists and is accessible
- Ensure boto3 is installed

### JWT Token Error
- Add SECRET_KEY to `.env` file
- Ensure token is sent in Authorization header: `Bearer <token>`
- Check token hasn't expired (30 days)

### File Upload Error
- Check file size (max 16MB)
- Verify file extension is allowed (png, jpg, jpeg, gif, webp)
- Ensure R2 storage is properly configured

## Next Steps

- [ ] Add email verification
- [ ] Implement password reset
- [ ] Add rate limiting
- [ ] Set up logging
- [ ] Add API documentation (Swagger/OpenAPI)
- [ ] Implement refresh tokens
- [ ] Add profile update endpoint
- [ ] Implement file deletion on user deletion

# HelpLink API

Flask API with Cloudflare R2 storage for user registration and authentication.

## Features

- User registration with file uploads (profile image, verification selfie, valid ID)
- User login with JWT authentication
- Cloudflare R2 storage integration for file uploads
- MySQL database integration
- Secure password hashing with bcrypt
- Protected routes with JWT tokens

## Prerequisites

- Python 3.8+
- MySQL database
- Cloudflare R2 storage account

## Installation

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Configure environment variables in `.env`:
```
DB_USER=james23
DB_PASSWORD=J@mes2410117
DB_HOST=179.61.246.136
DB_PORT=3306
DB_NAME=service_connect

r2_access_key=your_r2_access_key
r2_secret_key=your_r2_secret_key
r2_endpoint=your_r2_endpoint
r2_bucket_name=your_bucket_name

SECRET_KEY=your-secret-key-here
```

3. Run database migration to add password_hash field:
```bash
mysql -u james23 -p -h 179.61.246.136 service_connect < migrations/add_password_hash.sql
```

## Running the API

Start the Flask development server:
```bash
python app.py
```

The API will be available at `http://localhost:5000`

## API Endpoints

### Health Check
```
GET /health
```
Returns the health status of the API and database connection.

### User Registration
```
POST /api/auth/register
Content-Type: multipart/form-data
```

**Form Data:**
- `first_name` (required) - User's first name
- `last_name` (required) - User's last name
- `email` (required) - User's email address
- `password` (required) - User's password
- `address` (optional) - User's address
- `age` (optional) - User's age
- `number` (optional) - User's phone number
- `account_type` (optional) - Account type: beneficiary, donor, volunteer, verified_organization (default: beneficiary)
- `profile_image` (optional) - Profile image file (PNG, JPG, JPEG, GIF, WEBP)
- `verification_selfie` (optional) - Verification selfie file
- `valid_id` (optional) - Valid ID file

**Response:**
```json
{
  "message": "User registered successfully",
  "user": {
    "id": 1,
    "first_name": "John",
    "last_name": "Doe",
    "email": "john@example.com",
    "account_type": "beneficiary",
    "badge": "under_review",
    "profile_image": "profiles/uuid.jpg",
    "created_at": "2024-01-01T00:00:00"
  },
  "token": "jwt_token_here"
}
```

### User Login
```
POST /api/auth/login
Content-Type: application/json
```

**JSON Body:**
```json
{
  "email": "john@example.com",
  "password": "password123"
}
```

**Response:**
```json
{
  "message": "Login successful",
  "user": {
    "id": 1,
    "first_name": "John",
    "last_name": "Doe",
    "email": "john@example.com",
    "last_logon": "2024-01-01T00:00:00"
  },
  "token": "jwt_token_here"
}
```

### Get Current User
```
GET /api/auth/me
Authorization: Bearer <token>
```

Returns the authenticated user's information.

**Response:**
```json
{
  "user": {
    "id": 1,
    "first_name": "John",
    "last_name": "Doe",
    "email": "john@example.com"
  }
}
```

### Get File URL
```
GET /api/auth/file-url/<file_path>
Authorization: Bearer <token>
```

Generates a presigned URL for accessing a file stored in R2 storage.

**Response:**
```json
{
  "url": "https://presigned-url-here",
  "expires_in": 3600
}
```

## Quick Testing

Run the included test script:
```bash
python test_api.py
```

This will test all endpoints including registration, login, and authenticated requests.

## Testing with cURL

### Register a new user:
```bash
curl -X POST http://localhost:5000/api/auth/register \
  -F "first_name=John" \
  -F "last_name=Doe" \
  -F "email=john@example.com" \
  -F "password=password123" \
  -F "age=25" \
  -F "account_type=beneficiary" \
  -F "profile_image=@/path/to/image.jpg"
```

### Login:
```bash
curl -X POST http://localhost:5000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"john@example.com","password":"password123"}'
```

### Get current user:
```bash
curl -X GET http://localhost:5000/api/auth/me \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"
```

## Project Structure

```
HelpLink-Api/
├── app.py                      # Main Flask application (factory pattern)
├── requirements.txt            # Python dependencies
├── test_api.py                 # API test script
├── .env                        # Environment variables
├── .gitignore                  # Git ignore file
├── routes/
│   ├── __init__.py
│   └── auth.py                 # Authentication routes
├── models/
│   ├── __init__.py
│   └── auth_model.py           # User model and auth methods
├── utils/
│   ├── __init__.py
│   └── r2_storage.py           # R2 storage handler
└── migrations/
    └── add_password_hash.sql   # Database migration
```

## Application Architecture

The application uses:
- **Application Factory Pattern** - Clean initialization and configuration
- **Blueprint-based routing** - Modular route organization
- **Flask's g object** - Request-scoped database connections with automatic cleanup
- **Centralized error handling** - Consistent error responses
- **R2 Storage integration** - Initialized once at application startup

## Security Notes

- Passwords are hashed using bcrypt before storage
- JWT tokens expire after 30 days
- File uploads are validated for allowed extensions
- Maximum file upload size is 16MB
- All protected routes require valid JWT token

## Error Handling

The API returns appropriate HTTP status codes:
- `200` - Success
- `201` - Created
- `400` - Bad Request
- `401` - Unauthorized
- `409` - Conflict (e.g., email already exists)
- `500` - Internal Server Error

## License

MIT

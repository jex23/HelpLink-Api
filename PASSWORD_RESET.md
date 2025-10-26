# Password Reset Feature Documentation

This document describes the password reset functionality using OTP (One-Time Password) for the HelpLink API.

## Overview

The password reset feature uses a 3-step process:

1. **Request OTP** - User provides their email and receives an OTP code
2. **Verify OTP** - User submits the OTP code to verify it's valid (optional step)
3. **Reset Password** - User submits OTP code + new password to complete the reset

## Database Schema

The `user_otps` table stores all OTP codes:

```sql
CREATE TABLE user_otps (
    id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    user_id BIGINT UNSIGNED NOT NULL,
    otp_code VARCHAR(10) NOT NULL,
    type ENUM('email_verification', 'password_reset', 'login') NOT NULL DEFAULT 'password_reset',
    validity ENUM('active', 'inactive') NOT NULL DEFAULT 'active',
    is_used TINYINT(1) NOT NULL DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP DEFAULT (CURRENT_TIMESTAMP + INTERVAL 3 MINUTE),
    INDEX idx_user_id (user_id)
);
```

## Configuration

### Email Setup

Add these variables to your `.env` file:

```env
# SMTP Configuration
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=your-email@gmail.com
SMTP_PASSWORD=your-app-password
FROM_EMAIL=noreply@helplink.com
FROM_NAME=HelpLink
```

### Email Provider Options

#### Gmail
1. Use an App Password (not your regular password)
2. Generate at: https://myaccount.google.com/apppasswords
3. Settings:
   ```env
   SMTP_SERVER=smtp.gmail.com
   SMTP_PORT=587
   ```

#### SendGrid
1. Create an API key at https://app.sendgrid.com/settings/api_keys
2. Settings:
   ```env
   SMTP_SERVER=smtp.sendgrid.net
   SMTP_PORT=587
   SMTP_USERNAME=apikey
   SMTP_PASSWORD=your-sendgrid-api-key
   ```

#### Amazon SES
1. Create SMTP credentials in AWS SES console
2. Settings:
   ```env
   SMTP_SERVER=email-smtp.us-east-1.amazonaws.com
   SMTP_PORT=587
   SMTP_USERNAME=your-ses-username
   SMTP_PASSWORD=your-ses-password
   ```

## API Endpoints

### 1. Request Password Reset

**Endpoint:** `POST /api/auth/forgot-password`

**Description:** Generates an OTP code and sends it to the user's email.

**Request:**
```json
{
  "email": "user@example.com"
}
```

**Response:**
```json
{
  "message": "If the email exists, an OTP has been sent to it",
  "email": "user@example.com"
}
```

**Notes:**
- Returns the same response whether the email exists or not (security best practice)
- OTP is valid for 3 minutes
- Invalidates any previous active OTPs for the same user
- Sends a formatted email with the OTP code

**Example:**
```bash
curl -X POST http://localhost:5001/api/auth/forgot-password \
  -H "Content-Type: application/json" \
  -d '{
    "email": "john@example.com"
  }'
```

---

### 2. Verify OTP (Optional)

**Endpoint:** `POST /api/auth/verify-otp`

**Description:** Verifies if an OTP code is valid without using it. This is optional and can be used to provide user feedback before attempting password reset.

**Request:**
```json
{
  "email": "user@example.com",
  "otp_code": "123456",
  "otp_type": "password_reset"
}
```

**Response (Success):**
```json
{
  "message": "OTP verified successfully",
  "email": "user@example.com",
  "otp_valid": true
}
```

**Response (Error):**
```json
{
  "error": "Invalid or expired OTP code"
}
```

**Example:**
```bash
curl -X POST http://localhost:5001/api/auth/verify-otp \
  -H "Content-Type: application/json" \
  -d '{
    "email": "john@example.com",
    "otp_code": "123456",
    "otp_type": "password_reset"
  }'
```

---

### 3. Reset Password

**Endpoint:** `POST /api/auth/reset-password`

**Description:** Resets the user's password using a valid OTP code.

**Request:**
```json
{
  "email": "user@example.com",
  "otp_code": "123456",
  "new_password": "newSecurePassword123"
}
```

**Response (Success):**
```json
{
  "message": "Password reset successfully",
  "email": "user@example.com"
}
```

**Response (Error):**
```json
{
  "error": "Invalid or expired OTP code"
}
```

**Notes:**
- Password must be at least 6 characters
- OTP is marked as used after successful reset
- All active OTPs for the user are invalidated
- User will need to login with the new password

**Example:**
```bash
curl -X POST http://localhost:5001/api/auth/reset-password \
  -H "Content-Type: application/json" \
  -d '{
    "email": "john@example.com",
    "otp_code": "123456",
    "new_password": "myNewPassword123"
  }'
```

---

## Complete Password Reset Flow

Here's a typical password reset flow:

```bash
# Step 1: Request OTP
curl -X POST http://localhost:5001/api/auth/forgot-password \
  -H "Content-Type: application/json" \
  -d '{"email": "john@example.com"}'

# User receives email with OTP code: 123456

# Step 2 (Optional): Verify OTP
curl -X POST http://localhost:5001/api/auth/verify-otp \
  -H "Content-Type: application/json" \
  -d '{
    "email": "john@example.com",
    "otp_code": "123456"
  }'

# Step 3: Reset password with OTP
curl -X POST http://localhost:5001/api/auth/reset-password \
  -H "Content-Type: application/json" \
  -d '{
    "email": "john@example.com",
    "otp_code": "123456",
    "new_password": "myNewPassword123"
  }'

# Step 4: Login with new password
curl -X POST http://localhost:5001/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "email": "john@example.com",
    "password": "myNewPassword123"
  }'
```

## Security Features

1. **Time-Limited OTPs**
   - OTPs expire after 3 minutes
   - Configurable expiration time

2. **Single Use**
   - OTPs are marked as used after successful password reset
   - Cannot be reused

3. **Automatic Invalidation**
   - Previous OTPs are invalidated when a new one is requested
   - All OTPs are invalidated after password reset

4. **Email Verification**
   - OTP is sent to the registered email
   - Only the email owner can reset the password

5. **No Email Enumeration**
   - Same response whether email exists or not
   - Prevents attackers from discovering valid emails

6. **Password Requirements**
   - Minimum 6 characters
   - Hashed using bcrypt

## Email Template

The OTP email includes:
- User's name
- 6-digit OTP code
- Expiration time (3 minutes)
- Security warnings
- HTML and plain text versions

Example email:
```
Subject: Password Reset - HelpLink

Hello John Doe,

You requested to reset your password. Please use the following verification code:

┌─────────────┐
│   123456    │
└─────────────┘

Important:
- This code is valid for 3 minutes
- Do not share this code with anyone
- If you didn't request this code, please ignore this email

© 2025 HelpLink. All rights reserved.
```

## Development Mode

When SMTP is not configured (no `SMTP_USERNAME` or `SMTP_PASSWORD`), the system operates in development mode:

- Email sending is simulated
- OTP code is printed to console
- All endpoints work normally
- Useful for testing without email setup

Console output example:
```
Warning: SMTP not configured. Email would be sent to: john@example.com
Subject: Password Reset - HelpLink
OTP Code: 123456
```

## Error Handling

### Common Errors

| Status | Error | Cause |
|--------|-------|-------|
| 400 | No data provided | Missing request body |
| 400 | Email is required | Missing email field |
| 400 | Missing required fields | Missing email or otp_code |
| 400 | New password must be at least 6 characters | Password too short |
| 401 | Invalid OTP code | User not found |
| 401 | Invalid or expired OTP code | OTP is wrong, expired, or already used |
| 500 | Failed to generate OTP | Database error |
| 500 | Failed to update password | Database error |

## Frontend Integration Example

### React Example

```javascript
// 1. Request OTP
const requestPasswordReset = async (email) => {
  const response = await fetch('http://localhost:5001/api/auth/forgot-password', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ email })
  });
  return await response.json();
};

// 2. Verify OTP (optional)
const verifyOTP = async (email, otpCode) => {
  const response = await fetch('http://localhost:5001/api/auth/verify-otp', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      email,
      otp_code: otpCode,
      otp_type: 'password_reset'
    })
  });
  return await response.json();
};

// 3. Reset password
const resetPassword = async (email, otpCode, newPassword) => {
  const response = await fetch('http://localhost:5001/api/auth/reset-password', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      email,
      otp_code: otpCode,
      new_password: newPassword
    })
  });
  return await response.json();
};

// Usage
async function handlePasswordReset() {
  // Step 1: Request OTP
  await requestPasswordReset('john@example.com');

  // Step 2: User enters OTP from email
  const otp = prompt('Enter OTP from email:');

  // Step 3: Reset password
  const newPassword = 'newPassword123';
  const result = await resetPassword('john@example.com', otp, newPassword);
  console.log(result.message);
}
```

## OTP Management Functions

The system includes helper functions in `models/auth_model.py`:

```python
# Generate OTP
otp_code = AuthModel.generate_otp(length=6)

# Create OTP
otp_code = AuthModel.create_otp(conn, user_id, otp_type='password_reset', validity_minutes=3)

# Verify OTP
otp_record = AuthModel.verify_otp(conn, user_id, otp_code, otp_type='password_reset')

# Mark as used
AuthModel.mark_otp_as_used(conn, otp_id)

# Invalidate all OTPs
AuthModel.invalidate_user_otps(conn, user_id, otp_type='password_reset')
```

## Customization

### Change OTP Length
Edit `models/auth_model.py:178`:
```python
return ''.join(random.choices(string.digits, k=8))  # 8-digit OTP
```

### Change Validity Duration
When calling `create_otp()`:
```python
AuthModel.create_otp(conn, user_id, validity_minutes=5)  # 5 minutes
```

### Custom Email Template
Edit `utils/email_service.py:62` to customize the HTML template.

### Use for Other Purposes
The OTP system supports multiple types:
- `email_verification` - Verify email addresses
- `password_reset` - Reset passwords
- `login` - Two-factor authentication

## Testing

### Manual Testing
```bash
# 1. Request OTP
curl -X POST http://localhost:5001/api/auth/forgot-password \
  -H "Content-Type: application/json" \
  -d '{"email": "test@example.com"}'

# Check console for OTP code if SMTP not configured

# 2. Reset password
curl -X POST http://localhost:5001/api/auth/reset-password \
  -H "Content-Type: application/json" \
  -d '{
    "email": "test@example.com",
    "otp_code": "123456",
    "new_password": "newPassword123"
  }'
```

## Troubleshooting

### Email not received
1. Check SMTP credentials in `.env`
2. Check spam/junk folder
3. Verify console logs for errors
4. Test SMTP connection

### OTP invalid
1. Check if OTP is expired (3 minutes)
2. Verify correct email is used
3. Check if OTP was already used
4. Request a new OTP

### Password not updating
1. Check password length (min 6 characters)
2. Verify OTP is valid
3. Check database connection
4. Review server logs

## Production Recommendations

1. **Use a dedicated email service** (SendGrid, Amazon SES, Mailgun)
2. **Set appropriate rate limiting** on forgot-password endpoint
3. **Monitor OTP usage** for abuse
4. **Log all password reset attempts**
5. **Consider adding CAPTCHA** to prevent automated requests
6. **Send notification emails** when password is changed
7. **Add IP tracking** for security
8. **Implement account lockout** after multiple failed attempts

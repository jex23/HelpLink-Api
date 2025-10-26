# Password Reset Setup Guide

This guide will help you set up and use the password reset functionality that has been added to your HelpLink API.

## What Was Added

### New Files Created

1. **`utils/email_service.py`** - Email service for sending OTP codes
2. **`PASSWORD_RESET.md`** - Complete documentation
3. **`test_password_reset.py`** - Test suite
4. **`.env.example`** - Environment variables template

### Modified Files

1. **`models/auth_model.py`** - Added OTP management methods:
   - `generate_otp()` - Generate random OTP codes
   - `create_otp()` - Create and store OTP in database
   - `verify_otp()` - Verify OTP validity
   - `mark_otp_as_used()` - Mark OTP as used
   - `invalidate_user_otps()` - Invalidate all user OTPs

2. **`routes/auth.py`** - Added three new endpoints:
   - `POST /api/auth/forgot-password` - Request OTP
   - `POST /api/auth/verify-otp` - Verify OTP (optional)
   - `POST /api/auth/reset-password` - Reset password with OTP

3. **`app.py`** - Registered new endpoints in API listing

## Quick Start

### 1. Update Your Environment Variables

Add these to your `.env` file:

```bash
# Email Configuration (for Gmail)
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=your-email@gmail.com
SMTP_PASSWORD=your-app-password
FROM_EMAIL=noreply@helplink.com
FROM_NAME=HelpLink
```

**For Gmail:**
- Use an App Password (not your regular password)
- Create one at: https://myaccount.google.com/apppasswords
- Select "Mail" and your device, then generate

**For Testing (No Email):**
- Leave SMTP variables empty or undefined
- OTP will be printed to console
- All functionality works normally

### 2. Ensure Database Table Exists

The `user_otps` table should already be created. If not, run:

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

### 3. Test the Functionality

**Option A: Using the Test Script**

```bash
# Install requests if needed
pip install requests

# Run the test script
python test_password_reset.py
```

**Option B: Manual Testing with curl**

```bash
# 1. Request OTP
curl -X POST http://localhost:5001/api/auth/forgot-password \
  -H "Content-Type: application/json" \
  -d '{"email": "your-email@example.com"}'

# 2. Check email (or console) for OTP code

# 3. Verify OTP (optional)
curl -X POST http://localhost:5001/api/auth/verify-otp \
  -H "Content-Type: application/json" \
  -d '{
    "email": "your-email@example.com",
    "otp_code": "123456"
  }'

# 4. Reset password
curl -X POST http://localhost:5001/api/auth/reset-password \
  -H "Content-Type: application/json" \
  -d '{
    "email": "your-email@example.com",
    "otp_code": "123456",
    "new_password": "newPassword123"
  }'

# 5. Login with new password
curl -X POST http://localhost:5001/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "email": "your-email@example.com",
    "password": "newPassword123"
  }'
```

## How It Works

### Password Reset Flow

```
User                    API                     Database              Email
  |                      |                          |                    |
  |--forgot-password---->|                          |                    |
  |                      |--get user by email------>|                    |
  |                      |<-------------------------|                    |
  |                      |--create OTP------------->|                    |
  |                      |<-------------------------|                    |
  |                      |--send OTP email--------->|                    |
  |                      |                          |                    |--email-->User
  |<--success response---|                          |                    |
  |                      |                          |                    |
  |--reset-password----->|                          |                    |
  |   (with OTP)         |--verify OTP------------->|                    |
  |                      |<--OTP valid--------------|                    |
  |                      |--update password-------->|                    |
  |                      |--mark OTP as used------->|                    |
  |<--success------------|                          |                    |
```

### Security Features

1. **Time-Limited**: OTPs expire after 3 minutes
2. **Single-Use**: OTPs can only be used once
3. **Auto-Invalidation**: Previous OTPs invalidated on new request
4. **No Email Enumeration**: Same response for existing/non-existing emails
5. **Secure Storage**: Passwords hashed with bcrypt
6. **Database-Backed**: All OTPs tracked in database

## API Endpoints

### 1. Request Password Reset
```
POST /api/auth/forgot-password
Body: { "email": "user@example.com" }
```

### 2. Verify OTP (Optional)
```
POST /api/auth/verify-otp
Body: {
  "email": "user@example.com",
  "otp_code": "123456",
  "otp_type": "password_reset"
}
```

### 3. Reset Password
```
POST /api/auth/reset-password
Body: {
  "email": "user@example.com",
  "otp_code": "123456",
  "new_password": "newPassword123"
}
```

## Email Providers

### Gmail (Development)
```env
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=your-email@gmail.com
SMTP_PASSWORD=your-app-password
```

### SendGrid (Production)
```env
SMTP_SERVER=smtp.sendgrid.net
SMTP_PORT=587
SMTP_USERNAME=apikey
SMTP_PASSWORD=your-sendgrid-api-key
```

### Amazon SES (Production)
```env
SMTP_SERVER=email-smtp.us-east-1.amazonaws.com
SMTP_PORT=587
SMTP_USERNAME=your-ses-username
SMTP_PASSWORD=your-ses-password
```

## Customization

### Change OTP Length
Edit `models/auth_model.py:188`:
```python
def generate_otp(length=8):  # Change from 6 to 8
    return ''.join(random.choices(string.digits, k=length))
```

### Change OTP Validity
Edit `routes/auth.py:505`:
```python
otp_code = AuthModel.create_otp(conn, user['id'], validity_minutes=5)  # 5 minutes
```

### Customize Email Template
Edit `utils/email_service.py` - modify the HTML template in `send_otp_email()` method.

## Troubleshooting

### OTP not received in email
1. Check `.env` file has correct SMTP settings
2. Check spam/junk folder
3. Look at console logs - OTP printed if SMTP not configured
4. Verify email address is correct in database

### "Invalid or expired OTP code" error
1. OTP expires after 3 minutes - request new one
2. OTP can only be used once - request new one
3. Make sure you're using the most recent OTP
4. Verify email address matches

### Email service errors
1. Gmail: Make sure you're using App Password, not regular password
2. Check firewall isn't blocking port 587
3. Verify SMTP credentials are correct
4. Check logs for specific error messages

### OTP printed to console instead of emailed
- This is normal when SMTP is not configured
- Add SMTP settings to `.env` to enable email sending
- Useful for development/testing

## Production Checklist

Before deploying to production:

- [ ] Configure proper email service (SendGrid/SES recommended)
- [ ] Set up FROM_EMAIL with your domain
- [ ] Add rate limiting to prevent abuse
- [ ] Enable HTTPS for all endpoints
- [ ] Monitor OTP usage for suspicious activity
- [ ] Set up email delivery monitoring
- [ ] Add logging for all password reset attempts
- [ ] Consider adding CAPTCHA to prevent bots
- [ ] Test email deliverability
- [ ] Set up proper DNS records (SPF, DKIM) for your email domain

## Additional Features

The OTP system can be used for other purposes:

### Email Verification
```python
# Generate OTP for email verification
otp_code = AuthModel.create_otp(conn, user_id, otp_type='email_verification')
```

### Two-Factor Authentication
```python
# Generate OTP for login
otp_code = AuthModel.create_otp(conn, user_id, otp_type='login')
```

## Documentation

- **Complete API Documentation**: See `PASSWORD_RESET.md`
- **Environment Variables**: See `.env.example`
- **Test Suite**: Run `python test_password_reset.py`

## Support

If you encounter issues:
1. Check the troubleshooting section above
2. Review server logs for error messages
3. Test with the included test script
4. Verify database table exists and is accessible
5. Check SMTP configuration in `.env`

## Next Steps

1. Set up your email provider (Gmail for testing, SendGrid/SES for production)
2. Update `.env` with SMTP credentials
3. Run the test script to verify everything works
4. Integrate with your frontend application
5. Deploy to production with proper email service

---

**Note**: All password reset attempts are logged to the console. Monitor these logs for security purposes.

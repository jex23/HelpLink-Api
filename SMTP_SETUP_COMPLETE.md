# SMTP Setup Complete - Quick Reference

## What Was Updated

### 1. Email Service (`utils/email_service.py`)
- ✅ Now supports **SSL encryption** (port 465) - your Gmail configuration
- ✅ Also supports **TLS encryption** (port 587) - alternative option
- ✅ Reads from your `.env` file configuration
- ✅ Better error messages and logging

### 2. Password Reset Endpoints (`routes/auth.py`)
All three endpoints now have enhanced logging and properly retrieve user data from the `users` table:

- ✅ `POST /api/auth/forgot-password` - Retrieves user by email from database
- ✅ `POST /api/auth/verify-otp` - Validates OTP from database
- ✅ `POST /api/auth/reset-password` - Updates password in database

### 3. Environment Configuration

Your `.env` file should have these settings:

```env
SMTP_HOST=smtp.gmail.com
SMTP_PORT=465
SMTP_USERNAME=helplinkteam2025@gmail.com
SMTP_PASSWORD=hhghmxkdljnkhppq
SMTP_ENCRYPTION=ssl
SMTP_FROM_ADDRESS=helplinkteam2025@gmail.com
SMTP_FROM_NAME="HelpLink Team"
```

## How It Works

### Email Retrieval Flow

```
1. User requests password reset with email
   ↓
2. System queries database: SELECT * FROM users WHERE email = ?
   ↓
3. If user found:
   - Retrieves: user_id, first_name, last_name, email from users table
   - Generates OTP and stores in user_otps table
   - Sends email to address from users table
   ↓
4. Logs show:
   [Password Reset] Looking up user with email: test@example.com
   [Password Reset] User found - ID: 123, Name: John Doe
   [Password Reset] Sending OTP to email retrieved from database: test@example.com
   [Password Reset] OTP generated successfully for user ID: 123
   ✓ Email sent successfully to test@example.com
```

## Testing

### Test 1: Verify SMTP Connection

```bash
# Run the SMTP test script
python test_smtp.py
```

This will:
- Display your SMTP configuration
- Send a test OTP email
- Confirm if email was sent successfully

### Test 2: Test Complete Password Reset Flow

```bash
# Start your API server
python app.py

# In another terminal, test the flow
curl -X POST http://localhost:5001/api/auth/forgot-password \
  -H "Content-Type: application/json" \
  -d '{"email": "test@example.com"}'
```

**What happens:**
1. Server looks up user in database
2. Generates 6-digit OTP
3. Sends email via Gmail (helplinkteam2025@gmail.com)
4. Email received at user's address

### Test 3: Check Server Logs

When you run the forgot-password endpoint, you should see logs like:

```
[Password Reset] Looking up user with email: test@example.com
[Password Reset] User found - ID: 5, Name: John Doe
[Password Reset] Sending OTP to email retrieved from database: test@example.com
[Password Reset] OTP generated successfully for user ID: 5
✓ Email sent successfully to test@example.com
```

## Email Template

Users will receive an email like this:

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        HelpLink
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Hello John Doe,

You requested to reset your password. Please use the following verification code:

┌─────────────┐
│   123456    │
└─────────────┘

Important:
• This code is valid for 3 minutes
• Do not share this code with anyone
• If you didn't request this code, please ignore this email

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
© 2025 HelpLink. All rights reserved.
From: HelpLink Team <helplinkteam2025@gmail.com>
```

## Complete API Flow Example

### Step 1: Request OTP
```bash
curl -X POST http://localhost:5001/api/auth/forgot-password \
  -H "Content-Type: application/json" \
  -d '{
    "email": "user@example.com"
  }'
```

**Response:**
```json
{
  "message": "If the email exists, an OTP has been sent to it",
  "email": "user@example.com"
}
```

**Server Log:**
```
[Password Reset] Looking up user with email: user@example.com
[Password Reset] User found - ID: 123, Email: user@example.com
[Password Reset] OTP generated successfully for user ID: 123
✓ Email sent successfully to user@example.com
```

### Step 2: Verify OTP (Optional)
```bash
curl -X POST http://localhost:5001/api/auth/verify-otp \
  -H "Content-Type: application/json" \
  -d '{
    "email": "user@example.com",
    "otp_code": "123456"
  }'
```

**Response:**
```json
{
  "message": "OTP verified successfully",
  "email": "user@example.com",
  "otp_valid": true
}
```

### Step 3: Reset Password
```bash
curl -X POST http://localhost:5001/api/auth/reset-password \
  -H "Content-Type: application/json" \
  -d '{
    "email": "user@example.com",
    "otp_code": "123456",
    "new_password": "newSecurePassword123"
  }'
```

**Response:**
```json
{
  "message": "Password reset successfully",
  "email": "user@example.com"
}
```

**Server Log:**
```
[Password Reset] Looking up user with email: user@example.com
[Password Reset] User found - ID: 123, Email: user@example.com
[Password Reset] Verifying OTP for user ID: 123
[Password Reset] OTP verified, updating password for user ID: 123
[Password Reset] Password updated successfully for user ID: 123
[Password Reset] OTP marked as used (ID: 456)
[Password Reset] All active OTPs invalidated for user ID: 123
[Password Reset] Password reset completed successfully for user@example.com
```

### Step 4: Login with New Password
```bash
curl -X POST http://localhost:5001/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "email": "user@example.com",
    "password": "newSecurePassword123"
  }'
```

## Database Queries

The system executes these SQL queries:

### 1. Lookup User
```sql
SELECT * FROM users WHERE email = 'user@example.com'
```

### 2. Create OTP
```sql
-- Invalidate old OTPs
UPDATE user_otps
SET validity = 'inactive'
WHERE user_id = 123 AND type = 'password_reset' AND validity = 'active';

-- Insert new OTP
INSERT INTO user_otps (user_id, otp_code, type, validity, is_used, expires_at)
VALUES (123, '123456', 'password_reset', 'active', 0, NOW() + INTERVAL 3 MINUTE);
```

### 3. Verify OTP
```sql
SELECT * FROM user_otps
WHERE user_id = 123
  AND otp_code = '123456'
  AND type = 'password_reset'
  AND validity = 'active'
  AND is_used = 0
  AND expires_at > NOW()
ORDER BY created_at DESC
LIMIT 1;
```

### 4. Update Password
```sql
UPDATE users
SET password_hash = '$2b$12$...'
WHERE id = 123;
```

### 5. Mark OTP as Used
```sql
UPDATE user_otps
SET is_used = 1, validity = 'inactive'
WHERE id = 456;
```

## Troubleshooting

### Issue: Email not received

**Check:**
1. Server logs show "✓ Email sent successfully"
2. Check spam/junk folder
3. Verify email exists in users table:
   ```sql
   SELECT email FROM users WHERE email = 'test@example.com';
   ```

### Issue: "Invalid OTP code" error

**Check:**
1. OTP expires after 3 minutes
2. Request new OTP if expired
3. Check user_otps table:
   ```sql
   SELECT * FROM user_otps
   WHERE user_id = 123
   ORDER BY created_at DESC
   LIMIT 5;
   ```

### Issue: SMTP connection error

**Check:**
1. `.env` file has correct credentials
2. Port 465 requires `SMTP_ENCRYPTION=ssl`
3. Gmail app password is valid
4. Run `python test_smtp.py` to diagnose

## Summary

### What's Working ✅

- ✅ Email service configured with your Gmail credentials
- ✅ SSL encryption (port 465) properly implemented
- ✅ All endpoints retrieve data from `users` table
- ✅ OTPs stored and validated in `user_otps` table
- ✅ Comprehensive logging for debugging
- ✅ Email normalization (lowercase, trimmed)
- ✅ Security features (expiration, single-use, invalidation)

### Test Scripts Available

1. **`test_smtp.py`** - Test SMTP connection
2. **`test_password_reset.py`** - Test complete flow
3. **Manual testing** - Use curl commands above

### Next Steps

1. ✅ Verify `.env` has your SMTP credentials
2. ✅ Run `python test_smtp.py` to test email sending
3. ✅ Run `python app.py` to start the server
4. ✅ Test the complete password reset flow
5. ✅ Check server logs to see database interactions

---

**Your SMTP Configuration:**
- Host: smtp.gmail.com
- Port: 465 (SSL)
- From: helplinkteam2025@gmail.com
- Name: HelpLink Team

**All emails will be sent from `helplinkteam2025@gmail.com` to the email address stored in the `users` table!**

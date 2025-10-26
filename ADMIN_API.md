# HelpLink Admin API Documentation

This document describes the admin API endpoints for managing the HelpLink platform.

## Authentication

All admin endpoints require authentication via JWT token in the Authorization header:

```
Authorization: Bearer <your_jwt_token>
```

## Admin Access Control

The admin routes are currently protected by the `@admin_required` decorator in `routes/admin.py`.

**IMPORTANT**: You need to customize the admin access control to fit your needs. Open `routes/admin.py` and modify the `admin_required` decorator (lines 11-32) to implement your admin authentication logic.

### Options for Admin Access Control:

1. **Restrict to verified organizations:**
   ```python
   if current_user.get('account_type') != 'verified_organization':
       return jsonify({'error': 'Admin access required'}), 403
   ```

2. **Restrict to specific email addresses:**
   ```python
   admin_emails = ['admin@helplink.com', 'support@helplink.com']
   if current_user.get('email') not in admin_emails:
       return jsonify({'error': 'Admin access required'}), 403
   ```

3. **Add an `is_admin` field to users table** (recommended):
   ```sql
   ALTER TABLE users ADD COLUMN is_admin BOOLEAN DEFAULT FALSE;
   ```
   Then check:
   ```python
   if not current_user.get('is_admin'):
       return jsonify({'error': 'Admin access required'}), 403
   ```

---

## Endpoints

### Dashboard

#### GET `/api/admin/dashboard`
Get comprehensive dashboard overview including statistics and recent activity.

**Response:**
```json
{
  "statistics": {
    "users": {...},
    "posts": {...},
    "donations": {...},
    "supporters": {...},
    "comments": {...},
    "chats": {...},
    "messages": {...}
  },
  "recent_activity": [...],
  "pending_verifications": 5,
  "pending_donations": 3
}
```

---

## User Management

### GET `/api/admin/users`
Get all users with optional filtering.

**Query Parameters:**
- `limit` (optional, default: 50) - Number of records to return
- `offset` (optional, default: 0) - Number of records to skip
- `account_type` (optional) - Filter by account type: `beneficiary`, `donor`, `volunteer`, `verified_organization`
- `badge` (optional) - Filter by badge: `verified`, `under_review`

**Example:**
```
GET /api/admin/users?limit=20&account_type=donor&badge=verified
```

**Response:**
```json
{
  "users": [
    {
      "id": 1,
      "first_name": "John",
      "last_name": "Doe",
      "email": "john@example.com",
      "account_type": "donor",
      "badge": "verified",
      ...
    }
  ],
  "total": 150,
  "limit": 20,
  "offset": 0
}
```

### GET `/api/admin/users/verification-requests`
Get users pending verification (with `under_review` badge).

**Query Parameters:**
- `limit` (optional, default: 50)
- `offset` (optional, default: 0)

**Response:**
```json
{
  "users": [...],
  "total": 25,
  "limit": 50,
  "offset": 0
}
```

### PUT `/api/admin/users/:user_id/badge`
Update user's verification badge.

**Request Body:**
```json
{
  "badge": "verified"
}
```

**Valid badge values:** `verified`, `under_review`

**Response:**
```json
{
  "message": "User badge updated successfully",
  "user_id": 123,
  "badge": "verified"
}
```

### PUT `/api/admin/users/:user_id/account-type`
Update user's account type.

**Request Body:**
```json
{
  "account_type": "verified_organization"
}
```

**Valid account types:** `beneficiary`, `donor`, `volunteer`, `verified_organization`

**Response:**
```json
{
  "message": "Account type updated successfully",
  "user_id": 123,
  "account_type": "verified_organization"
}
```

---

## Post Management

### GET `/api/admin/posts`
Get all posts with optional filtering.

**Query Parameters:**
- `limit` (optional, default: 50)
- `offset` (optional, default: 0)
- `post_type` (optional) - Filter by type: `donation`, `request`
- `status` (optional) - Filter by status: `active`, `closed`, `pending`

**Example:**
```
GET /api/admin/posts?post_type=request&status=active
```

**Response:**
```json
{
  "posts": [
    {
      "id": 1,
      "user_id": 5,
      "post_type": "request",
      "title": "Need food assistance",
      "status": "active",
      "first_name": "Jane",
      "last_name": "Smith",
      ...
    }
  ],
  "total": 75,
  "limit": 50,
  "offset": 0
}
```

### PUT `/api/admin/posts/:post_id/status`
Update post status for moderation.

**Request Body:**
```json
{
  "status": "pending"
}
```

**Valid status values:** `active`, `closed`, `pending`

**Response:**
```json
{
  "message": "Post status updated successfully",
  "post_id": 456,
  "status": "pending"
}
```

---

## Comment Moderation

### GET `/api/admin/comments`
Get all comments with optional filtering.

**Query Parameters:**
- `limit` (optional, default: 50)
- `offset` (optional, default: 0)
- `status` (optional) - Filter by status: `visible`, `hidden`, `deleted`

**Example:**
```
GET /api/admin/comments?status=hidden
```

**Response:**
```json
{
  "comments": [
    {
      "id": 1,
      "post_id": 10,
      "user_id": 5,
      "content": "Comment text...",
      "status": "hidden",
      "first_name": "John",
      "post_title": "Post title",
      ...
    }
  ],
  "total": 200,
  "limit": 50,
  "offset": 0
}
```

### PUT `/api/admin/comments/:comment_id/status`
Update comment status for moderation.

**Request Body:**
```json
{
  "status": "hidden"
}
```

**Valid status values:** `visible`, `hidden`, `deleted`

**Response:**
```json
{
  "message": "Comment status updated successfully",
  "comment_id": 789,
  "status": "hidden"
}
```

---

## Donation Management

### GET `/api/admin/donations`
Get all donations with optional filtering.

**Query Parameters:**
- `limit` (optional, default: 50)
- `offset` (optional, default: 0)
- `verification_status` (optional) - Filter by status: `pending`, `ongoing`, `fulfilled`

**Example:**
```
GET /api/admin/donations?verification_status=pending
```

**Response:**
```json
{
  "donations": [
    {
      "id": 1,
      "post_id": 10,
      "user_id": 5,
      "amount": 100.00,
      "verification_status": "pending",
      "message": "Donation message...",
      "first_name": "John",
      "post_title": "Post title",
      "proofs": [
        {
          "image_url": "https://..."
        }
      ],
      ...
    }
  ],
  "total": 50,
  "limit": 50,
  "offset": 0
}
```

### PUT `/api/admin/donations/:donation_id/status`
Update donation verification status.

**Request Body:**
```json
{
  "verification_status": "fulfilled"
}
```

**Valid status values:** `pending`, `ongoing`, `fulfilled`

**Response:**
```json
{
  "message": "Donation status updated successfully",
  "donation_id": 123,
  "verification_status": "fulfilled"
}
```

---

## Supporter Management

### GET `/api/admin/supporters`
Get all supporters.

**Query Parameters:**
- `limit` (optional, default: 50)
- `offset` (optional, default: 0)

**Response:**
```json
{
  "supporters": [
    {
      "id": 1,
      "post_id": 10,
      "user_id": 5,
      "support_type": "volunteer",
      "message": "Support message...",
      "first_name": "Jane",
      "post_title": "Post title",
      "proofs": [
        {
          "image_url": "https://..."
        }
      ],
      ...
    }
  ],
  "total": 30,
  "limit": 50,
  "offset": 0
}
```

---

## Statistics & Analytics

### GET `/api/admin/statistics`
Get comprehensive platform statistics.

**Response:**
```json
{
  "users": {
    "total_users": 500,
    "beneficiaries": 200,
    "donors": 150,
    "volunteers": 100,
    "organizations": 50,
    "verified_users": 300,
    "pending_verification": 25
  },
  "posts": {
    "total_posts": 150,
    "donation_posts": 75,
    "request_posts": 75,
    "active_posts": 100,
    "closed_posts": 45,
    "pending_posts": 5
  },
  "donations": {
    "total_donations": 200,
    "total_amount": 50000.00,
    "average_amount": 250.00,
    "pending_donations": 10,
    "ongoing_donations": 15,
    "fulfilled_donations": 175
  },
  "supporters": {
    "total_supporters": 300,
    "shares": 150,
    "volunteers": 100,
    "advocates": 40,
    "others": 10
  },
  "comments": {
    "total_comments": 500,
    "visible_comments": 480,
    "hidden_comments": 15,
    "deleted_comments": 5
  },
  "chats": {
    "total_chats": 100,
    "private_chats": 90,
    "group_chats": 10
  },
  "messages": {
    "total_messages": 1000
  }
}
```

### GET `/api/admin/activity`
Get recent platform activity.

**Query Parameters:**
- `limit` (optional, default: 20)

**Response:**
```json
{
  "activities": [
    {
      "activity_type": "user_registered",
      "description": "John Doe registered",
      "activity_time": "2025-10-26T10:30:00",
      ...
    },
    {
      "activity_type": "post_created",
      "description": "Jane Smith created donation post: Help needed",
      "activity_time": "2025-10-26T10:25:00",
      ...
    },
    {
      "activity_type": "donation_made",
      "description": "Bob Johnson donated to: Help needed",
      "activity_time": "2025-10-26T10:20:00",
      ...
    }
  ],
  "count": 20
}
```

---

## Usage Examples

### Example 1: Verify a User
```bash
# Get verification requests
curl -X GET "http://localhost:5001/api/admin/users/verification-requests" \
  -H "Authorization: Bearer YOUR_TOKEN"

# Update user badge to verified
curl -X PUT "http://localhost:5001/api/admin/users/123/badge" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"badge": "verified"}'
```

### Example 2: Moderate a Post
```bash
# Get all pending posts
curl -X GET "http://localhost:5001/api/admin/posts?status=pending" \
  -H "Authorization: Bearer YOUR_TOKEN"

# Approve the post
curl -X PUT "http://localhost:5001/api/admin/posts/456/status" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"status": "active"}'
```

### Example 3: Process Donations
```bash
# Get pending donations
curl -X GET "http://localhost:5001/api/admin/donations?verification_status=pending" \
  -H "Authorization: Bearer YOUR_TOKEN"

# Mark donation as fulfilled
curl -X PUT "http://localhost:5001/api/admin/donations/789/status" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"verification_status": "fulfilled"}'
```

### Example 4: View Dashboard
```bash
curl -X GET "http://localhost:5001/api/admin/dashboard" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

---

## Notes

1. **Image URLs**: All image fields (profile images, verification documents, proof images) are automatically converted to presigned URLs valid for 7 days.

2. **Pagination**: Most list endpoints support pagination via `limit` and `offset` parameters.

3. **Error Handling**: All endpoints return appropriate HTTP status codes:
   - `200` - Success
   - `400` - Bad request (invalid parameters)
   - `401` - Unauthorized (missing or invalid token)
   - `403` - Forbidden (not admin)
   - `500` - Server error

4. **Admin Access**: Remember to configure the `admin_required` decorator in `routes/admin.py` before using in production!

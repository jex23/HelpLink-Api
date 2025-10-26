# Image Upload Guide - HelpLink API

## How Image Upload Works

### Flow:
1. **Client sends image** via `multipart/form-data`
2. **Flask receives file** in `request.files`
3. **File validation** checks allowed extensions (png, jpg, jpeg, gif, webp)
4. **Upload to R2** using `r2_storage.upload_file()`
5. **Get path** like `profiles/uuid-abc123.jpg`
6. **Store path in database** in the respective column

---

## Database Columns for Images

```sql
profile_image         VARCHAR(255)  -- stores: profiles/uuid.jpg
verification_selfie   VARCHAR(255)  -- stores: verifications/selfies/uuid.jpg
valid_id             VARCHAR(255)  -- stores: verifications/ids/uuid.jpg
```

**Important:** These columns store the **path/key**, not the full URL.

---

## How to Test Image Upload

### Using cURL:

```bash
curl -X POST http://localhost:5001/api/auth/register \
  -F "first_name=John" \
  -F "last_name=Doe" \
  -F "email=john@example.com" \
  -F "password=securepass123" \
  -F "profile_image=@/path/to/photo.jpg" \
  -F "verification_selfie=@/path/to/selfie.jpg" \
  -F "valid_id=@/path/to/id.jpg"
```

### Using Postman:

1. Set method to **POST**
2. URL: `http://localhost:5001/api/auth/register`
3. Go to **Body** tab
4. Select **form-data**
5. Add fields:
   - `first_name` = Text = "John"
   - `last_name` = Text = "Doe"
   - `email` = Text = "john@example.com"
   - `password` = Text = "securepass123"
   - `profile_image` = **File** = (select image file)
   - `verification_selfie` = **File** = (select image file)
   - `valid_id` = **File** = (select image file)

---

## Allowed File Types

Extensions: `.png`, `.jpg`, `.jpeg`, `.gif`, `.webp`

The check happens in `routes/auth.py:14-17`:
```python
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}
```

---

## What Gets Stored in Database

**Example:**
```json
{
  "profile_image": "profiles/a1b2c3d4-e5f6-7890-abcd-ef1234567890.jpg",
  "verification_selfie": "verifications/selfies/b2c3d4e5-f6a7-8901-bcde-f12345678901.jpg",
  "valid_id": "verifications/ids/c3d4e5f6-a7b8-9012-cdef-123456789012.jpg"
}
```

These are **R2 object keys** (paths), not full URLs.

---

## How to Retrieve Image URLs

After registration, use the `/api/auth/file-url/<path>` endpoint:

```bash
curl -X GET http://localhost:5001/api/auth/file-url/profiles/a1b2c3d4.jpg \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"
```

**Response:**
```json
{
  "url": "https://...presigned-url...",
  "expires_in": 3600
}
```

This presigned URL is valid for 1 hour and can be used to display the image.

---

## Common Issues & Solutions

### 1. Images not uploading
**Check:**
- Is the file field name correct? (`profile_image`, `verification_selfie`, `valid_id`)
- Is the content-type `multipart/form-data`?
- Is the file extension allowed?
- Check server logs for R2 upload errors

### 2. Path is NULL in database
**Causes:**
- File upload failed to R2
- Check R2 credentials in `.env`
- Check R2 bucket permissions

### 3. File type not allowed
**Error:** File extension not in allowed list
**Solution:** Only use: png, jpg, jpeg, gif, webp

---

## Testing Checklist

- [ ] Add `password_hash` column to database (if not exists)
- [ ] Verify R2 credentials in `.env`
- [ ] Test upload with valid image file
- [ ] Check server logs for upload path
- [ ] Verify path stored in database
- [ ] Test retrieving presigned URL
- [ ] Verify image is accessible via presigned URL

---

## R2 Configuration

Make sure these are set in `.env`:
```env
r2_access_key=your_access_key
r2_secret_key=your_secret_key
r2_endpoint=https://....r2.cloudflarestorage.com
r2_bucket_name=helplink
```

---

## Debugging

With the updated code, you'll see console output:
```
Profile image received: photo.jpg
Profile image uploaded to: profiles/uuid.jpg
```

If you don't see the "uploaded to" message, the upload failed.

-- Add password_hash column to users table
ALTER TABLE users
ADD COLUMN password_hash VARCHAR(255) NOT NULL AFTER valid_id;

-- Note: Run this migration before using the authentication system
-- mysql -u james23 -p -h 179.61.246.136 service_connect < migrations/add_password_hash.sql

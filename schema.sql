CREATE TABLE IF NOT EXISTS users (
  user_id VARCHAR(50) PRIMARY KEY,
  username VARCHAR(100),
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS attendance (
  id SERIAL PRIMARY KEY,
  user_id VARCHAR(50) REFERENCES users (user_id),
  timestamp TIMESTAMP,
  device_serial VARCHAR(50),
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_attendance_user_id ON attendance (user_id);

CREATE INDEX IF NOT EXISTS idx_attendance_timestamp ON attendance (timestamp);

-- -- Add unique constraint to prevent duplicate attendance records
-- ALTER TABLE attendance ADD CONSTRAINT unique_attendance_record UNIQUE (user_id, timestamp, device_serial);
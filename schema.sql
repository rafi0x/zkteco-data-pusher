CREATE TABLE IF NOT EXISTS zkt_users (
  user_id VARCHAR(50) PRIMARY KEY,
  username VARCHAR(100),
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS zkt_attendance (
  id SERIAL PRIMARY KEY,
  user_id VARCHAR(50) REFERENCES zkt_users (user_id),
  timestamp TIMESTAMP,
  device_serial VARCHAR(50),
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_zkt_attendance_user_id ON zkt_attendance (user_id);

CREATE INDEX IF NOT EXISTS idx_zkt_attendance_timestamp ON zkt_attendance (timestamp);
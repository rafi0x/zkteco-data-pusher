CREATE TABLE IF NOT EXISTS zkt_users (
  id SERIAL PRIMARY KEY,
  user_id VARCHAR(50),
  username VARCHAR(100),
  UNIQUE (user_id)
);

CREATE TABLE IF NOT EXISTS zkt_attendance (
  id SERIAL PRIMARY KEY,
  created_at TIMESTAMP DEFAULT NOW (),
  status VARCHAR(50) DEFAULT 'PENDING',
  timestamp VARCHAR(250),
  device_serial VARCHAR(150) DEFAULT '000000',
  user_id VARCHAR,
  UNIQUE (user_id, timestamp, device_serial)
);

CREATE INDEX IF NOT EXISTS idx_zkt_attendance_user_id ON zkt_attendance (user_id);

CREATE INDEX IF NOT EXISTS idx_zkt_attendance_timestamp ON zkt_attendance (timestamp);
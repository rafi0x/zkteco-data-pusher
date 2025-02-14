import psycopg2
from psycopg2.extras import execute_batch
import logging
from config import DB_CONFIG

class DatabaseHandler:
    def __init__(self):
        self.conn = None
        self.logger = logging.getLogger(__name__)

    def connect(self):
        try:
            self.conn = psycopg2.connect(**DB_CONFIG)
            self.logger.info("Successfully connected to database")
            return True
        except Exception as e:
            self.logger.error(f"Database connection error: {str(e)}")
            return False

    def disconnect(self):
        if self.conn:
            self.conn.close()
            self.logger.info("Database connection closed")

    def ensure_tables(self):
        """Create tables if they don't exist"""
        try:
            with self.conn.cursor() as cur:
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS zkt_users (
                        id SERIAL PRIMARY KEY,
                        user_id VARCHAR(50) UNIQUE,
                        username VARCHAR(100)
                    );

                    CREATE TABLE IF NOT EXISTS zkt_attendance (
                        id SERIAL PRIMARY KEY,
                        user_id VARCHAR(50),
                        timestamp TIMESTAMP,
                        device_serial VARCHAR(50),
                        UNIQUE (user_id, timestamp, device_serial)
                    );

                    CREATE INDEX IF NOT EXISTS idx_zkt_attendance_user_id 
                    ON zkt_attendance(user_id);
                    
                    CREATE INDEX IF NOT EXISTS idx_zkt_attendance_timestamp 
                    ON zkt_attendance(timestamp);
                """)
                self.conn.commit()
                return True
        except Exception as e:
            self.logger.error(f"Error ensuring tables: {str(e)}")
            self.conn.rollback()
            return False

    def is_attendance_empty(self):
        """Check if attendance table is empty"""
        try:
            with self.conn.cursor() as cur:
                cur.execute("SELECT COUNT(*) FROM zkt_attendance")
                count = cur.fetchone()[0]
                return count == 0
        except Exception as e:
            self.logger.error(f"Error checking attendance table: {str(e)}")
            return True

    def sync_users(self, users):
        """Sync users to database"""
        try:
            with self.conn.cursor() as cur:
                # Prepare data for batch insert/update
                user_data = [(user['user_id'], user['name']) for user in users]
                
                # Insert or update based on user_id
                for user_id, username in user_data:
                    cur.execute("""
                        WITH upsert AS (
                            UPDATE zkt_users 
                            SET username = %s,
                                updated_at = NOW()
                            WHERE user_id = %s
                            RETURNING *
                        )
                        INSERT INTO zkt_users (user_id, username, created_at, updated_at)
                        SELECT %s, %s, NOW(), NOW()
                        WHERE NOT EXISTS (SELECT * FROM upsert)
                    """, (username, user_id, user_id, username))
                
                self.conn.commit()
                self.logger.info(f"Successfully synced {len(users)} users")
                return True
        except Exception as e:
            self.logger.error(f"Error syncing users: {str(e)}")
            self.conn.rollback()
            return False

    def get_latest_attendance_timestamp(self):
        """Get the latest attendance timestamp"""
        try:
            with self.conn.cursor() as cur:
                # Modified to handle string timestamp
                cur.execute("SELECT MAX(CAST(timestamp AS timestamp)) FROM zkt_attendance")
                return cur.fetchone()[0]
        except Exception as e:
            self.logger.error(f"Error getting latest timestamp: {str(e)}")
            return None

    def get_attendance_count(self):
        """Get total number of attendance records in database"""
        try:
            with self.conn.cursor() as cur:
                cur.execute("SELECT COUNT(*) FROM zkt_attendance")
                return cur.fetchone()[0]
        except Exception as e:
            self.logger.error(f"Error getting attendance count: {str(e)}")
            return 0

    def get_attendance_count_by_device(self, device_serial):
        """Get total number of attendance records for specific device"""
        try:
            with self.conn.cursor() as cur:
                cur.execute("""
                    SELECT COUNT(*) FROM zkt_attendance 
                    WHERE device_serial = %s
                """, (device_serial,))
                return cur.fetchone()[0]
        except Exception as e:
            self.logger.error(f"Error getting attendance count for device {device_serial}: {str(e)}")
            return 0

    def clear_attendance_table(self):
        """Clear all records from attendance table"""
        try:
            with self.conn.cursor() as cur:
                cur.execute("TRUNCATE TABLE zkt_attendance")
                self.conn.commit()
                self.logger.info("Cleared attendance table")
                return True
        except Exception as e:
            self.logger.error(f"Error clearing attendance table: {str(e)}")
            self.conn.rollback()
            return False

    def save_attendance(self, records, device_serial):
        """Save attendance records to database"""
        try:
            # Try to save users if they exist
            unique_users = list({
                record['user_id']: {
                    'user_id': record['user_id'],
                    'name': f"User {record['user_id']}"
                }
                for record in records
            }.values())

            try:
                self.sync_users(unique_users)
            except Exception as e:
                self.logger.warning(f"Could not sync users, continuing anyway: {str(e)}")

            # Save attendance records in batches
            with self.conn.cursor() as cur:
                batch_size = 100
                for i in range(0, len(records), batch_size):
                    batch = records[i:i + batch_size]
                    for record in batch:
                        cur.execute("""
                            INSERT INTO zkt_attendance 
                            (user_id, timestamp, device_serial, status, created_at)
                            SELECT %s, %s, %s, %s, NOW()
                            WHERE NOT EXISTS (
                                SELECT 1 FROM zkt_attendance 
                                WHERE user_id = %s 
                                AND timestamp = %s 
                                AND device_serial = %s
                            )
                        """, (
                            record['user_id'],            # INSERT user_id
                            str(record['timestamp']),     # INSERT timestamp
                            device_serial,                # INSERT device_serial
                            'PENDING',                    # INSERT status
                            record['user_id'],            # WHERE user_id
                            str(record['timestamp']),     # WHERE timestamp
                            device_serial                 # WHERE device_serial
                        ))
                    
                self.conn.commit()
                self.logger.info(f"Saved {len(records)} attendance records")
                return True
                
        except Exception as e:
            self.logger.error(f"Error saving attendance: {str(e)}")
            if self.conn:
                self.conn.rollback()
            return False

    def sync_device_records(self, records, device_serial):
        """Full sync of device records"""
        try:
            old_count = self.get_attendance_count_by_device(device_serial)
            
            with self.conn.cursor() as cur:
                cur.execute("DELETE FROM zkt_attendance WHERE device_serial = %s", (device_serial,))
                
                # Batch insert all records
                batch_size = 100
                for i in range(0, len(records), batch_size):
                    batch = records[i:i + batch_size]
                    for record in batch:
                        cur.execute("""
                            INSERT INTO zkt_attendance 
                            (user_id, timestamp, device_serial, status, created_at)
                            VALUES (%s, %s, %s, %s, NOW())
                        """, (
                            record['user_id'],
                            str(record['timestamp']),
                            device_serial,
                            'PENDING'
                        ))
                
                self.conn.commit()
                new_count = self.get_attendance_count_by_device(device_serial)
                self.logger.info(f"Full sync completed for device {device_serial}. Records: {old_count} -> {new_count}")
                return True
        except Exception as e:
            self.logger.error(f"Error during full sync for device {device_serial}: {str(e)}")
            self.conn.rollback()
            return False

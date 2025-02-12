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
                # Drop existing tables if they exist
                cur.execute("""
                    DROP TABLE IF EXISTS zkt_attendance;
                    DROP TABLE IF EXISTS zkt_users;
                    
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
                        CONSTRAINT uq_attendance UNIQUE (user_id, timestamp, device_serial),
                        CONSTRAINT fk_user FOREIGN KEY (user_id) REFERENCES zkt_users(user_id)
                    );

                    CREATE INDEX IF NOT EXISTS idx_zkt_attendance_timestamp 
                    ON zkt_attendance(timestamp);
                """)
                self.conn.commit()
                self.logger.info("Database tables recreated")
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
                
                # Upsert query
                query = """
                    INSERT INTO zkt_users (user_id, username)
                    VALUES (%s, %s)
                    ON CONFLICT (user_id) 
                    DO UPDATE SET username = EXCLUDED.username
                """
                
                execute_batch(cur, query, user_data)
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
                cur.execute("SELECT MAX(timestamp) FROM zkt_attendance")
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

    def get_last_attendance_id(self):
        """Get the last attendance ID"""
        try:
            with self.conn.cursor() as cur:
                cur.execute("SELECT MAX(id) FROM zkt_attendance")
                result = cur.fetchone()[0]
                return result if result is not None else 0
        except Exception as e:
            self.logger.error(f"Error getting last attendance ID: {str(e)}")
            return 0

    def save_attendance(self, records, device_serial):
        """Save attendance records to database"""
        try:
            with self.conn.cursor() as cur:
                success_count = 0
                # Batch insert records with ON CONFLICT DO NOTHING
                attendance_data = [
                    (record['user_id'], record['timestamp'], device_serial)
                    for record in records
                ]
                
                execute_batch(cur, """
                    INSERT INTO zkt_attendance (user_id, timestamp, device_serial)
                    VALUES (%s, %s, %s)
                    ON CONFLICT (user_id, timestamp, device_serial) DO NOTHING
                """, attendance_data)
                
                self.conn.commit()
                return True
        except Exception as e:
            self.logger.error(f"Error saving attendance: {str(e)}")
            self.conn.rollback()
            return False

    def sync_device_records(self, records, device_serial):
        """Full sync of device records continuing from last ID"""
        try:
            last_id = self.get_last_attendance_id()
            
            with self.conn.cursor() as cur:
                # Clear only records for this device
                cur.execute("DELETE FROM zkt_attendance WHERE device_serial = %s", (device_serial,))
                
                # Batch insert all records
                attendance_data = [
                    (record['user_id'], record['timestamp'], device_serial)
                    for record in records
                ]
                
                execute_batch(cur, """
                    INSERT INTO zkt_attendance (user_id, timestamp, device_serial)
                    VALUES (%s, %s, %s)
                    ON CONFLICT (user_id, timestamp, device_serial) DO NOTHING
                """, attendance_data)
                
                self.conn.commit()
                return True
        except Exception as e:
            self.logger.error(f"Error during full sync: {str(e)}")
            self.conn.rollback()
            return False

    def has_device_records(self, device_serial):
        """Check if device already has records in database"""
        try:
            with self.conn.cursor() as cur:
                cur.execute("""
                    SELECT EXISTS (
                        SELECT 1 FROM zkt_attendance 
                        WHERE device_serial = %s
                    )
                """, (device_serial,))
                return cur.fetchone()[0]
        except Exception as e:
            self.logger.error(f"Error checking device records: {str(e)}")
            return False

    def get_latest_device_timestamp(self, device_serial):
        """Get latest timestamp for specific device"""
        try:
            with self.conn.cursor() as cur:
                cur.execute("""
                    SELECT MAX(timestamp) FROM zkt_attendance 
                    WHERE device_serial = %s
                """, (device_serial,))
                return cur.fetchone()[0]
        except Exception as e:
            self.logger.error(f"Error getting device timestamp: {str(e)}")
            return None

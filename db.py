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
                # Create tables
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS zkt_users (
                        user_id VARCHAR(50) PRIMARY KEY,
                        username VARCHAR(100),
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    );

                    CREATE TABLE IF NOT EXISTS zkt_attendance (
                        id SERIAL PRIMARY KEY,
                        user_id VARCHAR(50) REFERENCES zkt_users(user_id),
                        timestamp TIMESTAMP,
                        device_serial VARCHAR(50),
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    );

                    CREATE INDEX IF NOT EXISTS idx_zkt_attendance_user_id 
                    ON zkt_attendance(user_id);

                    CREATE INDEX IF NOT EXISTS idx_zkt_attendance_timestamp 
                    ON zkt_attendance(timestamp);
                """)
                self.conn.commit()
                self.logger.info("Database tables verified/created")
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
                    DO UPDATE SET username = EXCLUDED.username, updated_at = CURRENT_TIMESTAMP
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

    def save_attendance(self, records, device_serial):
        """Save attendance records to database"""
        try:
            with self.conn.cursor() as cur:
                success_count = 0
                for record in records:
                    # Simple insert without checking for duplicates
                    insert_query = """
                        INSERT INTO zkt_attendance (user_id, timestamp, device_serial)
                        VALUES (%s, %s, %s)
                    """
                    cur.execute(insert_query, (record['user_id'], record['timestamp'], device_serial))
                    success_count += 1
                    
                    # Debug logging
                    self.logger.debug(
                        f"Processed record - User: {record['user_id']}, "
                        f"Time: {record['timestamp']}, Device: {device_serial}"
                    )

                self.conn.commit()
                if success_count > 0:
                    self.logger.info(f"Successfully saved {success_count} new attendance records")
                return success_count > 0
        except Exception as e:
            self.logger.error(f"Error saving attendance: {str(e)}")
            self.conn.rollback()
            return False

    def sync_device_records(self, records, device_serial):
        """Full sync of device records"""
        try:
            # First get count before sync
            old_count = self.get_attendance_count()
            
            # Clear and reinsert all records for this device
            with self.conn.cursor() as cur:
                cur.execute("DELETE FROM zkt_attendance WHERE device_serial = %s", (device_serial,))
                
                # Batch insert all records
                attendance_data = [
                    (record['user_id'], record['timestamp'], device_serial)
                    for record in records
                ]
                
                execute_batch(cur, """
                    INSERT INTO zkt_attendance (user_id, timestamp, device_serial)
                    VALUES (%s, %s, %s)
                """, attendance_data)
                
                self.conn.commit()
                new_count = self.get_attendance_count()
                self.logger.info(f"Full sync completed. Records: {old_count} -> {new_count}")
                return True
        except Exception as e:
            self.logger.error(f"Error during full sync: {str(e)}")
            self.conn.rollback()
            return False

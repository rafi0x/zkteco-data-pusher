from zk import ZK, const
import logging
from datetime import datetime
import time
from config import DEVICES
from db import DatabaseHandler

class ZKTecoReader:
    def __init__(self, ip, port=4370):
        self.ip = ip
        self.port = port
        self.zk = ZK(ip, port=port, timeout=5)
        self.conn = None
        
        # Setup logging
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s'
        )
        self.logger = logging.getLogger(__name__)

    def connect(self):
        """Establish connection with the device with retry"""
        retry_count = 3
        while retry_count > 0:
            try:
                self.conn = self.zk.connect()
                self.logger.info(f"Successfully connected to device at {self.ip}")
                return True
            except Exception as e:
                retry_count -= 1
                self.logger.error(f"Connection attempt failed: {str(e)}")
                if retry_count > 0:
                    time.sleep(5)  # Wait 5 seconds before retry
                self.disconnect()  # Ensure clean disconnect before retry
        return False

    def disconnect(self):
        """Safely disconnect from the device"""
        if self.conn:
            self.conn.disconnect()
            self.logger.info("Disconnected from device")

    def get_attendance_logs(self):
        """Retrieve attendance logs from the device with retry"""
        if not self.conn:
            if not self.connect():
                return []

        try:
            attendance = self.conn.get_attendance()
            if not attendance:
                return []
                
            logs = []
            for record in attendance:
                try:
                    log = {
                        'user_id': str(record.user_id),  # Convert to string
                        'timestamp': record.timestamp,
                        'punch': getattr(record, 'punch', None),
                        'status': getattr(record, 'status', None),
                    }
                    logs.append(log)
                except AttributeError:
                    continue  # Skip invalid records
                    
            return logs

        except Exception as e:
            self.logger.error(f"Error getting attendance logs: {str(e)}")
            self.disconnect()  # Force disconnect on error
            return []

    def get_users(self):
        """Retrieve user information from the device"""
        try:
            if not self.conn:
                raise Exception("Device not connected")

            users = self.conn.get_users()
            user_list = []
            
            for user in users:
                user_data = {
                    'user_id': user.user_id,
                    'name': user.name,
                    'privilege': user.privilege,
                    'card': user.card,
                }
                user_list.append(user_data)
            
            self.logger.info(f"Successfully retrieved {len(user_list)} users")
            return user_list

        except Exception as e:
            self.logger.error(f"Error getting users: {str(e)}")
            return []

    def print_users(self):
        """Print detailed user information"""
        users = self.get_users()
        self.logger.info("=== User Details ===")
        for user in users:
            self.logger.info(pformat(user))
        self.logger.info("==================")
        return users

    def clear_attendance(self):
        """Clear attendance records from device"""
        try:
            if not self.conn:
                raise Exception("Device not connected")
            
            self.conn.clear_attendance()
            self.logger.info("Successfully cleared attendance records")
            return True
        except Exception as e:
            self.logger.error(f"Error clearing attendance: {str(e)}")
            return False

    def enable_realtime(self):
        """Enable realtime event monitoring"""
        try:
            if not self.conn:
                raise Exception("Device not connected")
            
            def attendance_handler(event):
                self.logger.info("=== Real-time Attendance Event ===")
                self.logger.info(f"User ID: {event.uid}")
                self.logger.info(f"Status: {event.status}")
                self.logger.info(f"Timestamp: {event.timestamp}")
                self.logger.info("================================")

            self.logger.info("Enabling realtime monitoring...")
            self.conn.enable_device()
            self.conn.set_attendance_callback(attendance_handler)
            return True
        except Exception as e:
            self.logger.error(f"Error enabling realtime events: {str(e)}")
            return False

    def monitor_attendance(self):
        """Monitor attendance continuously"""
        try:
            if not self.conn:
                raise Exception("Device not connected")
            
            print("\nStarting attendance monitor...")
            print("Press Ctrl+C to exit\n")

            # Get initial attendance data
            last_records = self.get_attendance_logs()
            last_count = len(last_records)
            
            # Print existing records
            print(f"\nExisting attendance records: {last_count}")
            for record in last_records[-5:]:  # Show last 5 records
                print(f"User: {record['user_id']} - Time: {record['timestamp']} - Status: {record['status']}")
            
            # Monitor for new records
            while True:
                time.sleep(2)  # Check every 2 seconds
                current_records = self.get_attendance_logs()
                current_count = len(current_records)
                
                if current_count > last_count:
                    # New records found
                    new_records = current_records[last_count:]
                    for record in new_records:
                        print("\n=== New Attendance Record ===")
                        print(f"User ID: {record['user_id']}")
                        print(f"Time: {record['timestamp']}")
                        print(f"Status: {record['status']}")
                        print("============================")
                    
                    last_count = current_count

        except KeyboardInterrupt:
            print("\nStopping attendance monitor...")
        except Exception as e:
            self.logger.error(f"Error monitoring attendance: {str(e)}")

    def get_device_info(self):
        """Get device information"""
        try:
            if not self.conn:
                raise Exception("Device not connected")
            
            # For ZKTeco devices that don't support get_device_info
            # we'll return a dict with basic information
            return {
                'ip': self.ip,
                'serial': self.ip,  # Using IP as serial number
                'model': 'Unknown'
            }
        except Exception as e:
            self.logger.error(f"Error getting device info: {str(e)}")
            return None

    def monitor_attendance_with_db(self, db_handler):
        """Monitor attendance and save to database"""
        while True:  # Keep trying to monitor
            try:
                if not self.conn and not self.connect():
                    self.logger.error("Failed to connect to device, retrying in 30 seconds...")
                    time.sleep(30)
                    continue

                device_info = self.get_device_info()
                device_serial = device_info['serial'] if device_info else self.ip
                
                # Initial sync of users and check for existing records
                users = self.get_users()
                if users:
                    db_handler.ensure_users_exist(users)
                
                if not db_handler.has_device_records(device_serial):
                    self.logger.info(f"Loading initial data for device {device_serial}")
                    current_records = self.get_attendance_logs()
                    if current_records:
                        db_handler.save_attendance(current_records, device_serial)
                
                # Monitoring loop
                while True:
                    time.sleep(5)  # Reduced polling frequency
                    
                    if not self.conn:
                        raise Exception("Device connection lost")
                        
                    latest_device_time = db_handler.get_latest_device_timestamp(device_serial)
                    current_records = self.get_attendance_logs()
                    
                    if current_records:
                        new_records = [
                            record for record in current_records
                            if latest_device_time is None or record['timestamp'] > latest_device_time
                        ]
                        
                        if new_records:
                            db_handler.save_attendance(new_records, device_serial)

            except Exception as e:
                self.logger.error(f"Monitoring error: {str(e)}")
                self.disconnect()
                time.sleep(30)  # Wait before reconnecting

def main():
    # Initialize database
    db_handler = DatabaseHandler()
    if not db_handler.connect():
        print("Failed to connect to database")
        return

    try:
        # Ensure database tables exist
        if not db_handler.ensure_tables():
            print("Failed to create database tables")
            return
            
        print("Database tables verified successfully")

        readers = []
        # Initialize all devices
        for device in DEVICES:
            reader = ZKTecoReader(device['ip'], device['port'])
            if reader.connect():
                readers.append(reader)
        
        if not readers:
            print("No devices connected!")
            return

        # Start monitoring threads for all devices
        import threading
        threads = []
        for reader in readers:
            thread = threading.Thread(
                target=reader.monitor_attendance_with_db,
                args=(db_handler,)
            )
            thread.daemon = True
            thread.start()
            threads.append(thread)

        print("\nMonitoring all devices. Press Ctrl+C to exit.")
        while True:
            time.sleep(1)

    except KeyboardInterrupt:
        print("\nStopping monitoring...")
    finally:
        for reader in readers:
            reader.disconnect()
        db_handler.disconnect()

if __name__ == "__main__":
    main()

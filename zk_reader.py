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
        """Establish connection with the device"""
        try:
            self.conn = self.zk.connect()
            self.logger.info(f"Successfully connected to device at {self.ip}")
            return True
        except Exception as e:
            self.logger.error(f"Failed to connect to device: {str(e)}")
            return False

    def disconnect(self):
        """Safely disconnect from the device"""
        if self.conn:
            self.conn.disconnect()
            self.logger.info("Disconnected from device")

    def get_attendance_logs(self):
        """Retrieve attendance logs from the device"""
        try:
            if not self.conn:
                raise Exception("Device not connected")

            # Get attendance
            attendance = self.conn.get_attendance()
            logs = []
            
            for record in attendance:
                log = {
                    'user_id': record.user_id,
                    'timestamp': record.timestamp,
                    'punch': record.punch,
                    'status': record.status,
                }
                logs.append(log)
            
            self.logger.info(f"Successfully retrieved {len(logs)} attendance records")
            return logs

        except Exception as e:
            self.logger.error(f"Error getting attendance logs: {str(e)}")
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
            return self.conn.get_serialnumber()
        except Exception as e:
            self.logger.error(f"Error getting device info: {str(e)}")
            return None

    def monitor_attendance_with_db(self, db_handler):
        """Monitor attendance and save to database"""
        try:
            if not self.conn:
                raise Exception("Device not connected")

            device_info = self.get_device_info()
            device_serial = device_info if device_info else self.ip
            
            print(f"\nMonitoring device: {self.ip} (Serial: {device_serial})")
            
            # Initial sync of users
            users = self.get_users()
            db_handler.sync_users(users)
            
            # Track last sync time
            last_full_sync = datetime.now()
            SYNC_INTERVAL = 30 * 60  # 30 minutes in seconds
            
            while True:
                current_records = self.get_attendance_logs()
                if current_records:
                    # Check for full sync every 30 minutes
                    if (datetime.now() - last_full_sync).seconds >= SYNC_INTERVAL:
                        db_count = db_handler.get_attendance_count_by_device(device_serial)
                        device_count = len(current_records)
                        
                        self.logger.info(f"Periodic check for device {device_serial} - DB records: {db_count}, Device records: {device_count}")
                        
                        if db_count != device_count:
                            self.logger.info(f"Database count mismatch for device {device_serial}. Performing full sync...")
                            if db_handler.sync_device_records(current_records, device_serial):
                                self.logger.info(f"Full sync completed successfully for device {device_serial}")
                        
                        last_full_sync = datetime.now()
                    
                    # Real-time monitoring
                    latest_db_timestamp = db_handler.get_latest_attendance_timestamp()
                    new_records = [
                        record for record in current_records
                        if latest_db_timestamp is None or record['timestamp'] > latest_db_timestamp
                    ]
                    
                    if new_records:
                        for record in new_records:
                            if db_handler.save_attendance([record], device_serial):
                                print(f"\nNew attendance: User {record['user_id']} at {record['timestamp']}")
                
                time.sleep(2)

        except Exception as e:
            self.logger.error(f"Error monitoring attendance: {str(e)}")

    def monitor_live_capture_with_db(self, db_handler):
        """Monitor live capture events and store in database"""
        try:
            if not self.conn:
                raise Exception("Device not connected")

            device_info = self.get_device_info()
            device_serial = device_info if device_info else self.ip
            
            print(f"\nMonitoring live events from device: {self.ip} (Serial: {device_serial})")
            
            # Initial sync of users
            users = self.get_users()
            db_handler.sync_users(users)

            # Enable real-time monitoring
            self.conn.enable_device()
            self.conn.cancel_capture()
            self.conn.verify_user()
            self.end_live_capture = False
            
            for event in self.conn.live_capture():
                if event is None:  # timeout
                    continue
                if self.end_live_capture:
                    break
                    
                # Convert event to record format
                record = {
                    'user_id': event.user_id,
                    'timestamp': event.timestamp
                }
                
                # Save to database
                if db_handler.save_attendance([record], device_serial):
                    print(f"\nLive event: User {record['user_id']} at {record['timestamp']}")
                
        except Exception as e:
            self.logger.error(f"Error monitoring live events: {str(e)}")
        finally:
            self.end_live_capture = True

def main():
    # Initialize database
    db_handler = DatabaseHandler()
    if not db_handler.connect():
        print("Failed to connect to database")
        return

    try:
        readers = []
        # Initialize all devices
        for device in DEVICES:
            reader = ZKTecoReader(device['ip'], device['port'])
            if reader.connect():
                readers.append(reader)
        
        if not readers:
            print("No devices connected!")
            return

        # First sync all users from all devices
        print("Performing initial sync of users from all devices...")
        all_users = {}
        for reader in readers:
            device_info = reader.get_device_info()
            print(f"Getting users from device: {device_info}")
            users = reader.get_users()
            for user in users:
                all_users[user['user_id']] = user

        # Sync combined users to database
        if all_users:
            print(f"Syncing {len(all_users)} users to database...")
            db_handler.sync_users(list(all_users.values()))

        # Now start attendance sync
        print("\nStarting attendance sync...")
        for reader in readers:
            device_info = reader.get_device_info()
            print(f"Device: {device_info}")
            device_serial = device_info if device_info else reader.ip
            logs = reader.get_attendance_logs()
            if logs:
                db_handler.save_attendance(logs, device_serial)

        # Start live monitoring on all devices
        print("\nStarting live monitoring on all devices...")
        import threading
        threads = []
        for reader in readers:
            thread = threading.Thread(
                target=reader.monitor_live_capture_with_db,
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
        # Signal all threads to stop
        for reader in readers:
            reader.end_live_capture = True
    finally:
        # Clean up
        for reader in readers:
            reader.disconnect()
        db_handler.disconnect()

if __name__ == "__main__":
    main()

# ZKTeco Attendance Data Pusher

A Python application that reads attendance data from ZKTeco biometric devices and stores it in a PostgreSQL database. The application supports multiple devices and provides real-time monitoring capabilities.

## Features

- Multi-device support
- Real-time attendance monitoring
- Automatic data synchronization
- PostgreSQL database integration
- Threaded device monitoring
- Resilient connection handling
- Detailed logging

## Prerequisites

- Python 3.8+
- PostgreSQL database
- ZKTeco device(s) on the local network
- Network connectivity to the devices

## Installation

1. Clone the repository:

2. Create and activate virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # Linux/Mac
# or
venv\Scripts\activate  # Windows
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Create PostgreSQL database:
```sql
CREATE DATABASE your_database;
```

5. Configure the application:
   - Edit `config.py` with your database credentials
   - Add your ZKTeco device IPs and ports

## Configuration

### Database Configuration
Edit `config.py`:
```python
DB_CONFIG = {
    'host': 'localhost',
    'database': 'your_database',
    'user': 'your_username',
    'password': 'your_password',
    'port': 5432
}
```

### Device Configuration
Add your devices to `config.py`:
```python
DEVICES = [
    {'ip': '192.168.0.105', 'port': 4370},
    {'ip': '192.168.0.106', 'port': 4370},
    # Add more devices as needed
]
```

## Usage

Run the application:
```bash
python zk_reader.py
```

The application will:
1. Connect to the database
2. Create necessary tables if they don't exist
3. Connect to all configured devices
4. Sync existing users and attendance data
5. Start real-time monitoring

## Database Schema

### ZKT_Users Table
- `user_id`: Primary key (from device)
- `username`: User's name
- `created_at`: Record creation timestamp
- `updated_at`: Record update timestamp

### ZKT_Attendance Table
- `id`: Auto-incrementing primary key
- `user_id`: Foreign key to users table
- `timestamp`: Attendance timestamp
- `device_serial`: Device identifier
- `created_at`: Record creation timestamp

## Running as a Service

For production deployment, see `server_setup.md` for instructions on:
- Setting up as a systemd service
- Using Screen
- Using PM2

## Logging

The application logs to stdout with the following format:
```
YYYY-MM-DD HH:MM:SS,mmm - LEVEL - Message
```
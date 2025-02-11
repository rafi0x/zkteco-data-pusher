# ZKTeco Attendance Reader - Server Setup Guide

This guide explains different methods to run the ZKTeco attendance reader as a background service.

## Table of Contents
- [Method 1: Systemd Service (Recommended)](#method-1-systemd-service-recommended)
- [Method 2: Screen](#method-2-screen)
- [Method 3: PM2](#method-3-pm2)

## Method 1: Systemd Service (Recommended)

### Create Service File
```bash
sudo nano /etc/systemd/system/zkteco-reader.service
```

### Service Configuration
```ini
[Unit]
Description=ZKTeco Attendance Reader Service
After=network.target

[Service]
Type=simple
User=your_username
WorkingDirectory=/path/to/your/project
Environment="PATH=/path/to/your/project/venv/bin"
ExecStart=/path/to/your/project/venv/bin/python zk_reader.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

### Enable and Start Service
```bash
sudo systemctl enable zkteco-reader
sudo systemctl start zkteco-reader
```

### Monitor Service
```bash
sudo systemctl status zkteco-reader
sudo journalctl -u zkteco-reader -f
```

## Method 2: Screen

### Installation
```bash
sudo apt-get install screen
```

### Create Startup Script
Create `start.sh`:
```bash
#!/bin/bash
cd /path/to/your/project
source venv/bin/activate
python zk_reader.py
```

### Make Script Executable
```bash
chmod +x start.sh
```

### Start Screen Session
```bash
screen -dmS zkteco ./start.sh
```

### Monitor Screen Session
```bash
screen -r zkteco
```

## Method 3: PM2

### Installation
```bash
npm install -g pm2
```

### Start Application
```bash
pm2 start zk_reader.py --name "zkteco-reader" --interpreter /path/to/your/project/venv/bin/python
pm2 save
pm2 startup
```

### Monitor PM2 Process
```bash
pm2 logs zkteco-reader
pm2 status
```

## Notes
- Replace `/path/to/your/project` with your actual project path
- Replace `your_username` with your system username
- Choose the method that best suits your environment and requirements
- Systemd is recommended for Linux servers as it provides better system integration
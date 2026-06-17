#!/bin/bash

echo "🛡️ Dot - Installation"
echo "======================"

# ۱. copy files to /opt/dot
echo "📦 Copying files to /opt/dot..."
sudo mkdir -p /opt/dot
sudo cp -r "$(dirname "$0")"/* /opt/dot/

# ۲. files locking
echo "🔒 Locking files..."
sudo chown -R root:root /opt/dot
sudo chmod -R 755 /opt/dot
sudo chattr +i /opt/dot/main.py
sudo chattr +i /opt/dot/core/watcher.py
sudo chattr +i /opt/dot/core/logger.py
sudo chattr +i /opt/dot/core/config.py

# ۳. createing systemd service
echo "⚙️ Creating systemd service..."
sudo tee /etc/systemd/system/dot.service > /dev/null << EOF
[Unit]
Description=Dot Privacy Indicator
After=graphical-session-pre.target
Wants=graphical-session-pre.target

[Service]
ExecStart=/opt/dot/.venv/bin/python3 /opt/dot/main.py
User=$USER
Restart=always
RestartSec=1
Environment=DBUS_SESSION_BUS_ADDRESS=unix:path=/run/user/\$(id -u)/bus
Environment=DISPLAY=:0

[Install]
WantedBy=graphical-session.target
EOF

# ۴. service start
echo "🚀 Enabling service..."
sudo systemctl daemon-reload
sudo systemctl enable dot.service
sudo systemctl start dot.service

echo ""
echo "✅ Dot installed successfully!"
echo "   - Files locked in /opt/dot"
echo "   - systemd service: dot.service"
echo ""
echo "Check status: systemctl status dot.service"

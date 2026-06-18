#!/bin/bash

echo "🛡️ Dot - Installation"
echo "======================"

# 1. copy files to /opt/dot
echo "📦 Copying files to /opt/dot..."
sudo mkdir -p /opt/dot
sudo chown $USER:$USER /opt/dot
sudo cp -r "$(dirname "$0")"/* /opt/dot/

# 2. Creating virtual environment
echo "🐍 Creating virtual environment..."
python3 -m venv /opt/dot/.venv --system-site-packages
/opt/dot/.venv/bin/pip install psutil pyyaml

# 3. files locking
echo "🔒 Locking files..."
sudo chown -R root:root /opt/dot
sudo chmod -R 755 /opt/dot
sudo chattr +i /opt/dot/main.py
sudo chattr +i /opt/dot/core/watcher.py
sudo chattr +i /opt/dot/core/logger.py
sudo chattr +i /opt/dot/core/config.py

# 4. create systemd service
echo "⚙️ Creating systemd service..."
mkdir -p ~/.config/systemd/user/
cat > ~/.config/systemd/user/dot.service << 'EOF'
[Unit]
Description=Dot Privacy Indicator
After=graphical-session-pre.target
Wants=graphical-session-pre.target

[Service]
ExecStart=/opt/dot/.venv/bin/python3 /opt/dot/main.py
Restart=always
RestartSec=2
Environment=DBUS_SESSION_BUS_ADDRESS=unix:path=/run/user/%U/bus

[Install]
WantedBy=graphical-session.target
EOF

# 5. startup service
echo "🚀 Enabling service..."
systemctl --user daemon-reload
systemctl --user enable dot.service
systemctl --user start dot.service

echo ""
echo "✅ Dot installed successfully!"
echo "   - Files locked in /opt/dot"
echo "   - systemd user service: dot.service"
echo ""
echo "Check status: systemctl --user status dot.service"

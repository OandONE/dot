#!/bin/bash

echo "🛡️ Dot - Installation"
echo "======================"

# 1. copy files to /opt/dot
echo "📦 Copying files to /opt/dot..."
sudo mkdir -p /opt/dot
sudo chown $USER:$USER /opt/dot
sudo cp -r "$(dirname "$0")"/* /opt/dot/
sudo cp -r "$(dirname "$0")"/assets /opt/dot/ 2>/dev/null

# 1.5 sudo no password chattr/chown
echo "$USER ALL=(ALL) NOPASSWD: /usr/bin/chattr, /usr/bin/chown" | sudo tee /etc/sudoers.d/dot > /dev/null
sudo chmod 440 /etc/sudoers.d/dot

# 2. install packages
echo "🔍 Detecting distribution..."
if grep -qi "debian" /etc/os-release && ! grep -qi "ubuntu" /etc/os-release; then
    echo "📦 Debian detected. Installing packages..."
    sudo apt update
    sudo apt install python3-gi python3-gi-cairo gir1.2-ayatanaappindicator3-0.1 xdotool python3-venv python3-pip gnome-shell-extension-appindicator -y
else
    echo "📦 Ubuntu detected. Installing packages..."
    sudo apt update
    sudo apt install python3-gi python3-gi-cairo gir1.2-appindicator3-0.1 xdotool python3-venv python3-pip -y
fi

# 3. Creating virtual environment
echo "🐍 Creating virtual environment..."
python3 -m venv /opt/dot/.venv --system-site-packages
/opt/dot/.venv/bin/pip install psutil pyyaml

# 4. files locking
echo "🔒 Locking files..."
sudo chown $USER:$USER /opt/dot/config.yaml
sudo chmod 644 /opt/dot/config.yaml

sudo chattr -i /opt/dot/config.yaml 2>/dev/null
sudo chown $USER:$USER /opt/dot/config.yaml
sudo chmod 644 /opt/dot/config.yaml

sudo chown root:root /opt/dot/main.py /opt/dot/core/*.py /opt/dot/ui/*.py
sudo chmod 755 /opt/dot/main.py /opt/dot/core/*.py /opt/dot/ui/*.py
sudo chattr +i /opt/dot/main.py
sudo chattr +i /opt/dot/core/watcher.py
sudo chattr +i /opt/dot/core/logger.py
sudo chattr +i /opt/dot/core/config.py

# 5. create systemd service
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

# 6. startup service
echo "🚀 Enabling service..."
systemctl --user daemon-reload
systemctl --user enable dot.service
systemctl --user start dot.service

if ! grep -q "alias dot=" ~/.bash_aliases 2>/dev/null; then
    echo "alias dot='python3 /opt/dot/cli.py'" >> ~/.bash_aliases
fi

echo ""
echo "✅ Dot installed successfully!"
echo "   - Files locked in /opt/dot"
echo "   - systemd user service: dot.service"
echo ""
echo "👉 Run this to activate CLI: source ~/.bashrc"
echo "   Then try: dot help"

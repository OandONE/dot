import os
import subprocess

def update_desktop_entry():
    desktop_dir = os.path.expanduser("~/.local/share/applications")
    desktop_file = os.path.join(desktop_dir, "dot.desktop")
    
    os.makedirs(desktop_dir, exist_ok=True)

    home = os.path.expanduser("~")
    
    content = f"""[Desktop Entry]
Type=Application
Name=Dot
Comment=Privacy Indicator - Monitor microphone and camera access
Exec=python3 {home}/Dot/dot/main.py
Icon=security-high
StartupNotify=false
Terminal=false
Categories=Utility;Security;
Keywords=privacy;microphone;camera;indicator;monitor;
"""
    
    with open(desktop_file, 'w') as f:
        f.write(content)
    
    os.chmod(desktop_file, 0o755)
    
    subprocess.run(['update-desktop-database', desktop_dir],
                   capture_output=True)

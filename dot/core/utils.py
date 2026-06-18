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

def detect_distro():
    try:
        with open('/etc/os-release') as f:
            for line in f:
                if line.startswith('ID='):
                    distro = line.split('=')[1].strip().strip('"')
                    if 'ubuntu' in distro:
                        return 'ubuntu'
                    elif 'debian' in distro:
                        return 'debian'
    except:
        pass
    return 'other'

def get_appindicator_module():
    distro = detect_distro()
    if distro == 'debian':
        return 'AyatanaAppIndicator3', '0.1'
    return 'AppIndicator3', '0.1'


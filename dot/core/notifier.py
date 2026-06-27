import subprocess
from core.config import load_config

class Notifier:
    def __init__(self):
        self.last_notification = {}
    
    def notify(self, device, process_name, status):
        """Send Notify"""
        
        config = load_config()
        notifications = config.get('notifications', {})
        if not notifications.get(device, True):
            return
        
        key = f"{device}_{process_name}"
        
        if self.last_notification.get(key) == status:
            return
        
        self.last_notification[key] = status
        
        if status == 'started':
            title = f"🔴 {device.capitalize()} in use"
            message = f"{process_name} is using your {device}"
        else:
            title = f"🟢 {device.capitalize()} released"
            message = f"{process_name} stopped using your {device}"
        
        try:
            subprocess.run([
                'notify-send',
                title,
                message,
                '--icon=security-high',
                '--app-name=Dot',
                '--expire-time=5000'
            ])
        except:
            pass

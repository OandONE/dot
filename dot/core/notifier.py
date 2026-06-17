import subprocess
import os

class Notifier:
    def __init__(self):
        self.last_notification = {}
    
    def notify(self, device, process_name, status):
        """ارسال نوتیفیکیشن فقط وقتی وضعیت تغییر کنه"""
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

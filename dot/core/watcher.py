import subprocess
import psutil
from datetime import datetime
from core.logger import Logger
from core.config import load_config
from core.notifier import Notifier

class Watcher:
    def __init__(self, config):
        self.config = config
        self.active_devices = {}
        self.logger = Logger()
        self.notifier = Notifier()
        self.previous_mic_pids = set()
        self.previous_cam_pids = set()
        self.mic_start_time = {}
        self.cam_start_time = {}

    def check_all(self):
        self.config = load_config()
        if self.config['devices']['microphone']:
            self.check_microphone()
        if self.config['devices']['camera']:
            self.check_camera()
        return True

    def check_microphone(self):
        try:
            import json
            result = subprocess.run(
                ['pw-dump'],
                capture_output=True, text=True, timeout=3
            )
            
            if result.returncode != 0:
                return
                
            data = json.loads(result.stdout)
            processes = []
            
            for obj in data:
                info = obj.get('info', {})
                props = info.get('props', {})
                
                media_class = props.get('media.class', '')
                if media_class in ['Stream/Input/Audio', 'Stream/Input/Video']:
                    client_id = props.get('client.id', '')
                    if client_id:
                        for client_obj in data:
                            if str(client_obj.get('id', '')) == str(client_id):
                                client_props = client_obj.get('info', {}).get('props', {})
                                app_name = client_props.get('application.name', 'unknown')
                                app_pid = client_props.get('application.process.id', '')
                                
                                if app_pid:
                                    try:
                                        proc = psutil.Process(int(app_pid))
                                        processes.append({
                                            'pid': str(app_pid),
                                            'name': proc.name() if proc else app_name,
                                            'foreground': self._is_foreground(app_pid)
                                        })
                                    except:
                                        pass
                                break
            
            seen_pids = set()
            unique_processes = []
            for p in processes:
                if p['pid'] not in seen_pids:
                    seen_pids.add(p['pid'])
                    unique_processes.append(p)
            
            self.active_devices['microphone'] = unique_processes if unique_processes else None
            
            current_pids = set(p['pid'] for p in unique_processes)

            for pid in self.previous_mic_pids - current_pids:
                if pid in self.mic_start_time:
                    start = self.mic_start_time.pop(pid)
                    duration = int((datetime.now() - start).total_seconds())
                    if duration > 0:
                        self.logger.log_access('microphone', 'ended', pid, duration)
            
            for pid in current_pids - self.previous_mic_pids:
                self.mic_start_time[pid] = datetime.now()
            
            for p in unique_processes:
                if p['pid'] not in self.previous_mic_pids:
                    self.notifier.notify('microphone', p['name'], 'started')
            
            for pid in self.previous_mic_pids:
                if pid not in current_pids:
                    self.notifier.notify('microphone', 'unknown', 'stopped')
            
            for pid in self.previous_mic_pids - current_pids:
                if pid in self.mic_start_time:
                    duration = (datetime.now() - self.mic_start_time.pop(pid)).seconds
                    self.logger.log_access('microphone', 'ended', pid, duration)
            
            if current_pids and current_pids != self.previous_mic_pids:
                for p in unique_processes:
                    if p['pid'] in current_pids - self.previous_mic_pids:
                        self.logger.log_access('microphone', p['name'], p['pid'])
            
            self.previous_mic_pids = current_pids
                
        except Exception as e:
            print(f"[MIC] Error: {e}")

    def check_camera(self):
        try:
            result = subprocess.run(['fuser', '/dev/video0'], 
                                  capture_output=True, text=True)
            if result.stdout:
                pids = result.stdout.strip().split()
                processes = []
                for pid in pids:
                    try:
                        proc = psutil.Process(int(pid))
                        if proc.name() in ['pipewire', 'pulseaudio', 'wireplumber']:
                            continue
                        processes.append({
                            'pid': pid,
                            'name': proc.name(),
                            'foreground': self._is_foreground(pid)
                        })
                    except:
                        pass
                self.active_devices['camera'] = processes if processes else None
                
                current_pids = set(p['pid'] for p in processes)

                for pid in self.previous_cam_pids - current_pids:
                    if pid in self.cam_start_time:
                        start = self.cam_start_time.pop(pid)
                        duration = int((datetime.now() - start).total_seconds())
                        if duration > 0:
                            self.logger.log_access('camera', 'ended', pid, duration)
            
                if current_pids and current_pids != self.previous_cam_pids:
                    for p in processes:
                        self.logger.log_access('camera', p['name'], p['pid'])
                
                self.previous_cam_pids = current_pids

                for p in processes:
                    if p['pid'] not in self.previous_cam_pids:
                        self.notifier.notify('camera', p['name'], 'started')
                for pid in self.previous_cam_pids:
                    if pid not in current_pids:
                        self.notifier.notify('camera', 'unknown', 'stopped')
            else:
                self.active_devices['camera'] = None
        except:
            self.active_devices['camera'] = None

    def _is_foreground(self, pid):
        try:
            import subprocess
            result = subprocess.run(
                ['gdbus', 'call', '--session',
                 '--dest', 'org.gnome.Shell',
                 '--object-path', '/org/gnome/Shell',
                 '--method', 'org.gnome.Shell.Eval',
                 'global.display.focus_window?.get_wm_class() || ""'],
                capture_output=True, text=True, timeout=2
            )
            
            if result.stdout and "'" in result.stdout:
                active_class = result.stdout.split("'")[1] if result.stdout.count("'") >= 2 else ""
                
                if active_class:
                    try:
                        proc = psutil.Process(int(pid))
                        proc_name = proc.name().lower()
                        active_class = active_class.lower()
                        
                        if proc_name in active_class or active_class in proc_name:
                            return True
                    except:
                        pass
            
            return False
        except:
            return False

    def get_status(self):
        all_processes = []
        
        for device, processes in self.active_devices.items():
            if processes:
                all_processes.extend(processes)
        
        if not all_processes:
            return 'idle', None
        
        unique_pids = set(p['pid'] for p in all_processes)
        
        if len(unique_pids) > 1:
            return 'multiple', all_processes
        else:
            return 'active', all_processes

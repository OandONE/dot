import sqlite3
import os
from datetime import datetime

class Logger:
    def __init__(self):
        db_dir = os.path.join(os.path.dirname(__file__), '..', 'data')
        os.makedirs(db_dir, exist_ok=True)
        self.db_path = os.path.join(db_dir, 'dot.db')
        self.init_db()
    
    def init_db(self):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS access_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                device TEXT NOT NULL,
                process TEXT NOT NULL,
                pid INTEGER,
                duration INTEGER DEFAULT 0
            )
        """)
        conn.commit()
        conn.close()
    
    def log_access(self, device, process, pid, duration=0):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        cursor.execute(
            "INSERT INTO access_log (timestamp, device, process, pid, duration) VALUES (?, ?, ?, ?, ?)",
            (timestamp, device, process, pid, duration)
        )
        conn.commit()
        conn.close()

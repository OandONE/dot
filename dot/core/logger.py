"""SQLite-backed access history."""

import os
import sqlite3
from contextlib import closing
from datetime import datetime


class Logger:
    def __init__(self):
        db_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "data"))
        os.makedirs(db_dir, exist_ok=True)
        self.db_path = os.path.join(db_dir, "dot.db")
        self.init_db()

    def _connect(self):
        # A short busy timeout helps when the web panel and monitor access the
        # database around the same time.
        return sqlite3.connect(self.db_path, timeout=5)

    def init_db(self):
        with closing(self._connect()) as connection:
            with connection:
                connection.execute(
                    """
                    CREATE TABLE IF NOT EXISTS access_log (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        timestamp TEXT NOT NULL,
                        device TEXT NOT NULL,
                        process TEXT NOT NULL,
                        pid INTEGER,
                        duration INTEGER DEFAULT 0
                    )
                    """
                )

    def log_access(self, device, process, pid, duration=0):
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with closing(self._connect()) as connection:
            with connection:
                connection.execute(
                    "INSERT INTO access_log "
                    "(timestamp, device, process, pid, duration) "
                    "VALUES (?, ?, ?, ?, ?)",
                    (timestamp, device, process, pid, duration),
                )

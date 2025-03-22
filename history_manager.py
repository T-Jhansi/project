# history_manager.py
import sqlite3
from datetime import datetime
import json

class HistoryManager:
    def __init__(self):
        self.conn = sqlite3.connect('documentation_history.db', check_same_thread=False)
        self.create_history_table()
    
    def create_history_table(self):
        query = '''CREATE TABLE IF NOT EXISTS documentation_history
                  (id INTEGER PRIMARY KEY AUTOINCREMENT,
                   username TEXT,
                   code TEXT,
                   documentation TEXT,
                   created_at DATETIME,
                   FOREIGN KEY (username) REFERENCES users(username))'''
        self.conn.execute(query)
        self.conn.commit()
    
    def add_entry(self, username: str, code: str, documentation: str):
        self.conn.execute(
            'INSERT INTO documentation_history (username, code, documentation, created_at) VALUES (?, ?, ?, ?)',
            (username, code, documentation, datetime.now())
        )
        self.conn.commit()
    
    def get_user_history(self, username: str, limit: int = 10):
        cursor = self.conn.execute(
            'SELECT * FROM documentation_history WHERE username=? ORDER BY created_at DESC LIMIT ?',
            (username, limit)
        )
        return cursor.fetchall()
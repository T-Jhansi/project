# auth.py
import streamlit as st
from datetime import datetime
import sqlite3
import hashlib

class Auth:
    def __init__(self):
        self.conn = sqlite3.connect('users.db', check_same_thread=False)
        self.create_users_table()
    
    def create_users_table(self):
        query = '''CREATE TABLE IF NOT EXISTS users
                  (username TEXT PRIMARY KEY,
                   password TEXT,
                   created_at DATETIME)'''
        self.conn.execute(query)
        self.conn.commit()
    
    def hash_password(self, password):
        return hashlib.sha256(password.encode()).hexdigest()
    
    def register_user(self, username, password):
        hashed_pwd = self.hash_password(password)
        try:
            self.conn.execute(
                'INSERT INTO users VALUES (?, ?, ?)',
                (username, hashed_pwd, datetime.now())
            )
            self.conn.commit()
            return True
        except sqlite3.IntegrityError:
            return False
    
    def login_user(self, username, password):
        hashed_pwd = self.hash_password(password)
        cursor = self.conn.execute(
            'SELECT * FROM users WHERE username=? AND password=?',
            (username, hashed_pwd)
        )
        return cursor.fetchone() is not None
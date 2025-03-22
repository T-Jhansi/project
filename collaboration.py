# collaboration.py
import sqlite3
from datetime import datetime
from typing import List, Dict
import json
import logging

logger = logging.getLogger(__name__)

class CollaborationManager:
    def __init__(self):
        self.conn = sqlite3.connect('collaboration.db', check_same_thread=False)
        self.create_tables()
    
    def create_tables(self):
        """Create necessary tables for collaboration features"""
        queries = [
            '''CREATE TABLE IF NOT EXISTS shared_docs
               (id INTEGER PRIMARY KEY AUTOINCREMENT,
                doc_id TEXT,
                owner TEXT,
                shared_with TEXT,
                permissions TEXT,
                created_at DATETIME)''',
            
            '''CREATE TABLE IF NOT EXISTS comments
               (id INTEGER PRIMARY KEY AUTOINCREMENT,
                doc_id TEXT,
                user TEXT,
                comment TEXT,
                created_at DATETIME)''',
            
            '''CREATE TABLE IF NOT EXISTS notifications
               (id INTEGER PRIMARY KEY AUTOINCREMENT,
                user TEXT,
                message TEXT,
                read BOOLEAN,
                created_at DATETIME)'''
        ]
        
        for query in queries:
            self.conn.execute(query)
        self.conn.commit()
    
    def share_document(self, doc_id: str, owner: str, shared_with: str, permissions: Dict):
        """Share a document with another user"""
        try:
            self.conn.execute(
                'INSERT INTO shared_docs (doc_id, owner, shared_with, permissions, created_at) VALUES (?, ?, ?, ?, ?)',
                (doc_id, owner, shared_with, json.dumps(permissions), datetime.now())
            )
            self.conn.commit()
            
            # Create notification
            self.add_notification(
                shared_with,
                f"Document {doc_id} has been shared with you by {owner}"
            )
            return True
        except Exception as e:
            logger.error(f"Error sharing document: {str(e)}")
            return False
    
    def add_comment(self, doc_id: str, user: str, comment: str):
        """Add a comment to a document"""
        try:
            self.conn.execute(
                'INSERT INTO comments (doc_id, user, comment, created_at) VALUES (?, ?, ?, ?)',
                (doc_id, user, comment, datetime.now())
            )
            self.conn.commit()
            
            # Get document owner
            cursor = self.conn.execute(
                'SELECT owner FROM shared_docs WHERE doc_id=?',
                (doc_id,)
            )
            owner = cursor.fetchone()
            
            if owner:
                self.add_notification(
                    owner[0],
                    f"New comment on document {doc_id} by {user}"
                )
            return True
        except Exception as e:
            logger.error(f"Error adding comment: {str(e)}")
            return False
    
    def get_comments(self, doc_id: str) -> List[Dict]:
        """Get all comments for a document"""
        try:
            cursor = self.conn.execute(
                'SELECT * FROM comments WHERE doc_id=? ORDER BY created_at DESC',
                (doc_id,)
            )
            return [
                {
                    'id': row[0],
                    'user': row[2],
                    'comment': row[3],
                    'created_at': row[4]
                }
                for row in cursor.fetchall()
            ]
        except Exception as e:
            logger.error(f"Error getting comments: {str(e)}")
            return []
    
    def add_notification(self, user: str, message: str):
        """Add a notification for a user"""
        try:
            self.conn.execute(
                'INSERT INTO notifications (user, message, read, created_at) VALUES (?, ?, ?, ?)',
                (user, message, False, datetime.now())
            )
            self.conn.commit()
            return True
        except Exception as e:
            logger.error(f"Error adding notification: {str(e)}")
            return False
    
    def get_notifications(self, user: str) -> List[Dict]:
        """Get all notifications for a user"""
        try:
            cursor = self.conn.execute(
                'SELECT * FROM notifications WHERE user=? ORDER BY created_at DESC',
                (user,)
            )
            return [
                {
                    'id': row[0],
                    'message': row[2],
                    'read': row[3],
                    'created_at': row[4]
                }
                for row in cursor.fetchall()
            ]
        except Exception as e:
            logger.error(f"Error getting notifications: {str(e)}")
            return []
    
    def mark_notification_read(self, notification_id: int):
        """Mark a notification as read"""
        try:
            self.conn.execute(
                'UPDATE notifications SET read=? WHERE id=?',
                (True, notification_id)
            )
            self.conn.commit()
            return True
        except Exception as e:
            logger.error(f"Error marking notification read: {str(e)}")
            return False
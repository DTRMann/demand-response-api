# -*- coding: utf-8 -*-
"""
Created on Fri Apr 25 14:28:46 2025

@author: DTRManning
"""

from contextlib import contextmanager
import sqlite3

def init_db():
    
    """Initialize database tables and indexes"""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        # Create main events table
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS events (
            id TEXT PRIMARY KEY,
            start_time TEXT NOT NULL,
            end_time TEXT NOT NULL,
            requesting_entity TEXT NOT NULL,
            message TEXT,
            timezone TEXT NOT NULL,
            metadata TEXT
        )
        ''')
        
        # Create indexes for common query patterns
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_start_time ON events(start_time)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_end_time ON events(end_time)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_entity ON events(requesting_entity)')
        
        conn.commit()

@contextmanager
def get_db_connection():
    
    """Context manager for database connections"""
    conn = sqlite3.connect('events.db')
    conn.row_factory = sqlite3.Row  # This lets us access columns by name
    try:
        yield conn
    finally:
        conn.close()


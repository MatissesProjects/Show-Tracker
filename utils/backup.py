import shutil
import os
import sqlite3
from datetime import datetime

def is_database_empty(db_path):
    """Checks if the database has any media records."""
    if not os.path.exists(db_path):
        return True
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        # Check if media table exists
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='media'")
        if not cursor.fetchone():
            conn.close()
            return True
        
        cursor.execute("SELECT count(*) FROM media")
        count = cursor.fetchone()[0]
        conn.close()
        return count == 0
    except Exception:
        return True

def backup_database(db_path='show_tracker.db', backup_dir='backups'):
    """
    Creates a timestamped backup of the database file if it contains data.
    Keeps only the last 10 backups to save space.
    """
    if not os.path.exists(db_path) or is_database_empty(db_path):
        return None

    if not os.path.exists(backup_dir):
        os.makedirs(backup_dir)

    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    backup_filename = f"show_tracker_{timestamp}.db"
    backup_path = os.path.join(backup_dir, backup_filename)

    try:
        shutil.copy2(db_path, backup_path)
        
        # Cleanup old backups (keep last 10)
        backups = sorted([os.path.join(backup_dir, f) for f in os.listdir(backup_dir) if f.endswith('.db')])
        if len(backups) > 10:
            for old_backup in backups[:-10]:
                os.remove(old_backup)
                
        return backup_path
    except Exception as e:
        print(f"Backup failed: {e}")
        return None

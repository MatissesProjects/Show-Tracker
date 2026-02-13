import shutil
import os
from datetime import datetime

def backup_database(db_path='show_tracker.db', backup_dir='backups'):
    """
    Creates a timestamped backup of the database file.
    Keeps only the last 5 backups to save space.
    """
    if not os.path.exists(db_path):
        return None

    if not os.path.exists(backup_dir):
        os.makedirs(backup_dir)

    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    backup_filename = f"show_tracker_{timestamp}.db"
    backup_path = os.path.join(backup_dir, backup_filename)

    try:
        shutil.copy2(db_path, backup_path)
        
        # Cleanup old backups (keep last 5)
        backups = sorted([os.path.join(backup_dir, f) for f in os.listdir(backup_dir) if f.endswith('.db')])
        if len(backups) > 5:
            for old_backup in backups[:-5]:
                os.remove(old_backup)
                
        return backup_path
    except Exception as e:
        print(f"Backup failed: {e}")
        return None

import sqlite3
conn = sqlite3.connect('show_tracker.db')
cursor = conn.cursor()
try:
    cursor.execute('ALTER TABLE media ADD COLUMN in_watchlist BOOLEAN DEFAULT 0')
    conn.commit()
    print('Watchlist column added')
except Exception as e:
    print(f'Info: {e}')
conn.close()
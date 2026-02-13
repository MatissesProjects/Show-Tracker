import sqlite3
conn = sqlite3.connect('show_tracker.db')
cursor = conn.cursor()
try:
    cursor.execute('ALTER TABLE media ADD COLUMN poster_url VARCHAR(500)')
    conn.commit()
    print('Poster column added')
except Exception as e:
    print(f'Info: {e}')
conn.close()
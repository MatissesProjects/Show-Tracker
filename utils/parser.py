import csv
import io
from datetime import datetime
from models import Media, WatchHistory

def parse_netflix_history(csv_file_content, db):
    """
    Parses Netflix 'ViewingActivity.csv'. 
    Netflix format: Title, Date
    """
    stream = io.StringIO(csv_file_content.decode('utf-8'))
    reader = csv.DictReader(stream)
    
    new_entries = 0
    for row in reader:
        title = row.get('Title')
        date_str = row.get('Date')
        
        if not title or not date_str:
            continue
            
        try:
            watch_date = datetime.strptime(date_str, '%m/%d/%y')
        except ValueError:
            try:
                watch_date = datetime.strptime(date_str, '%Y-%m-%d')
            except ValueError:
                continue

        # Use db.session.query for more robust context handling
        media = db.session.query(Media).filter_by(title=title).first()
        if not media:
            media = Media(title=title, media_type='unknown')
            db.session.add(media)
            db.session.flush()

        existing_history = db.session.query(WatchHistory).filter_by(
            media_id=media.id, 
            watch_date=watch_date
        ).first()
        
        if not existing_history:
            history = WatchHistory(media_id=media.id, watch_date=watch_date, platform='Netflix')
            db.session.add(history)
            new_entries += 1
            
    db.session.commit()
    return new_entries

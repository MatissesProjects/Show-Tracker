import csv
import io
from datetime import datetime
from models import Media, WatchHistory
from utils.title_cleaner import clean_netflix_title

def parse_netflix_history(csv_file_content, db):
    """
    Parses Netflix 'ViewingActivity.csv'. 
    Netflix format: Title, Date
    """
    # Try decoding with utf-8-sig (handles BOM) first, then fallback to latin-1
    try:
        decoded_content = csv_file_content.decode('utf-8-sig')
    except UnicodeDecodeError:
        decoded_content = csv_file_content.decode('latin-1')

    stream = io.StringIO(decoded_content)
    reader = csv.DictReader(stream)
    
    new_entries = 0
    for row in reader:
        title = row.get('Title')
        date_str = row.get('Date')
        
        if not title or not date_str:
            continue
            
        base_title = clean_netflix_title(title)
            
        try:
            watch_date = datetime.strptime(date_str, '%m/%d/%y')
        except ValueError:
            try:
                watch_date = datetime.strptime(date_str, '%Y-%m-%d')
            except ValueError:
                continue

        # Use db.session.query for more robust context handling
        media = db.session.query(Media).filter_by(title=base_title).first()
        if not media:
            media = Media(title=base_title, media_type='unknown')
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

import csv
import io
from datetime import datetime
from models import Media, WatchHistory
from app import db

def parse_netflix_history(csv_file_content):
    """
    Parses Netflix 'ViewingActivity.csv'. 
    Netflix format: Title, Date
    """
    stream = io.StringIO(csv_file_content.decode('utf-8'))
    reader = csv.DictReader(stream)
    
    new_entries = 0
    for row in reader:
        # Netflix CSV columns are usually 'Title' and 'Date'
        title = row.get('Title')
        date_str = row.get('Date')
        
        if not title or not date_str:
            continue
            
        # Parse date (MM/DD/YY or YYYY-MM-DD depending on locale)
        try:
            watch_date = datetime.strptime(date_str, '%m/%d/%y')
        except ValueError:
            try:
                watch_date = datetime.strptime(date_str, '%Y-%m-%d')
            except ValueError:
                continue

        # Check if media already exists
        media = Media.query.filter_by(title=title).first()
        if not media:
            media = Media(title=title, media_type='unknown') # TMDB will enrich this later
            db.session.add(media)
            db.session.flush() # Get the ID

        # Check if this specific watch entry already exists
        existing_history = WatchHistory.query.filter_by(
            media_id=media.id, 
            watch_date=watch_date
        ).first()
        
        if not existing_history:
            history = WatchHistory(media_id=media.id, watch_date=watch_date, platform='Netflix')
            db.session.add(history)
            new_entries += 1
            
    db.session.commit()
    return new_entries

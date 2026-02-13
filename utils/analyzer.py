from sqlalchemy import func
from database import db
from models import Media, Person, MediaPerson, WatchHistory

def get_top_people(limit=20):
    """
    Ranks people by how many times they appear in the user's watch history.
    Optimized to handle large datasets by grouping media first.
    """
    # 1. Get watch counts for each media item
    watch_counts = db.session.query(
        WatchHistory.media_id,
        func.count(WatchHistory.id).label('count')
    ).group_by(WatchHistory.media_id).subquery()

    # 2. Join with MediaPerson and Person to get talent ranks
    query = db.session.query(
        Person.name,
        MediaPerson.role,
        func.sum(watch_counts.c.count).label('total_plays')
    ).join(MediaPerson, Person.id == MediaPerson.person_id) \
     .join(watch_counts, MediaPerson.media_id == watch_counts.c.media_id) \
     .group_by(Person.name, MediaPerson.role) \
     .order_by(func.sum(watch_counts.c.count).desc()) \
     .limit(limit)
    
    results = query.all()
    
    return [
        {'name': r[0], 'role': r[1], 'count': int(r[2])}
        for r in results
    ]

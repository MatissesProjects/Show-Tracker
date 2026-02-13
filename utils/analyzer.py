from sqlalchemy import func
from database import db
from models import Media, Person, MediaPerson, WatchHistory

def get_top_people(limit=20):
    """
    Ranks people by how many times they appear in the user's watch history.
    Returns a list of dicts with name, role, and count.
    """
    # Join WatchHistory -> Media -> MediaPerson -> Person
    query = db.session.query(
        Person.name,
        MediaPerson.role,
        func.count(WatchHistory.id).label('watch_count')
    ).join(MediaPerson, Person.id == MediaPerson.person_id) 
     .join(Media, Media.id == MediaPerson.media_id) 
     .join(WatchHistory, Media.id == WatchHistory.media_id) 
     .group_by(Person.name, MediaPerson.role) 
     .order_by(func.count(WatchHistory.id).desc()) 
     .limit(limit)
    
    results = query.all()
    
    return [
        {'name': r[0], 'role': r[1], 'count': r[2]}
        for r in results
    ]

from sqlalchemy import func
from database import db
from models import Media, Person, MediaPerson, WatchHistory

def get_top_people(limit=20):
    """
    Ranks people by the number of unique shows/movies the user has watched.
    """
    # 1. Get unique media IDs that have at least one watch entry
    watched_media_ids = db.session.query(WatchHistory.media_id).distinct()

    # 2. Join with MediaPerson and Person to count unique shows per person
    query = db.session.query(
        Person.name,
        MediaPerson.role,
        func.count(MediaPerson.media_id).label('show_count')
    ).join(MediaPerson, Person.id == MediaPerson.person_id) \
     .filter(MediaPerson.media_id.in_(watched_media_ids)) \
     .group_by(Person.name, MediaPerson.role) \
     .order_by(func.count(MediaPerson.media_id).desc()) \
     .limit(limit)
    
    results = query.all()
    
    return [
        {'name': r[0], 'role': r[1], 'count': r[2]}
        for r in results
    ]

def get_genre_stats():
    """
    Calculates genre preferences based on unique shows watched.
    """
    # Get all unique media that has been watched
    watched_media = db.session.query(Media).join(
        WatchHistory, Media.id == WatchHistory.media_id
    ).distinct().all()
    
    genre_counts = {}
    for media in watched_media:
        if media.genres:
            genres = media.genres.split(', ')
            for g in genres:
                genre_counts[g] = genre_counts.get(g, 0) + 1
                
    # Sort by count
    sorted_genres = sorted(genre_counts.items(), key=lambda x: x[1], reverse=True)
    return [{'name': g[0], 'count': g[1]} for g in sorted_genres]

import json

def get_thematic_stats():
    """
    Calculates thematic DNA preferences based on unique shows watched.
    """
    watched_media = db.session.query(Media).join(
        WatchHistory, Media.id == WatchHistory.media_id
    ).distinct().all()
    
    stats = {
        'themes': {},
        'moods': {},
        'aesthetics': {}
    }
    
    for media in watched_media:
        if media.thematic_metadata:
            try:
                dna = json.loads(media.thematic_metadata)
                for t in dna.get('themes', []):
                    stats['themes'][t] = stats['themes'].get(t, 0) + 1
                for m in dna.get('mood', []):
                    stats['moods'][m] = stats['moods'].get(m, 0) + 1
                for a in dna.get('aesthetic', []):
                    stats['aesthetics'][a] = stats['aesthetics'].get(a, 0) + 1
            except: pass
            
    # Format and sort
    result = {}
    for key in stats:
        sorted_items = sorted(stats[key].items(), key=lambda x: x[1], reverse=True)
        result[key] = [{'name': item[0], 'count': item[1]} for item in sorted_items]
        
    return result

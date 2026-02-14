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

def get_thematic_stats():
    """
    Calculates unified DNA preferences (talent, genres, themes, moods, aesthetics, tropes).
    """
    watched_media = db.session.query(Media).join(
        WatchHistory, Media.id == WatchHistory.media_id
    ).distinct().all()
    
    stats = {
        'talent': {},
        'genres': {},
        'themes': {},
        'moods': {},
        'aesthetics': {},
        'tropes': {}
    }
    
    for media in watched_media:
        # Calculate weight based on rating (same as taste profile)
        weight = 0.2
        if media.user_rating == 2: weight = 1.0
        elif media.user_rating == 1: weight = 0.7
        elif media.user_rating == -1: continue 

        # Talent
        for mp in media.person_memberships:
            name = mp.person.name
            stats['talent'][name] = stats['talent'].get(name, 0) + weight
            
        # Genres
        if media.genres:
            for g in media.genres.split(', '):
                stats['genres'][g] = stats['genres'].get(g, 0) + weight

        # AI DNA
        if media.thematic_metadata:
            try:
                dna = json.loads(media.thematic_metadata)
                for key in ['themes', 'mood', 'aesthetic', 'tropes']:
                    target_key = 'moods' if key == 'mood' else ('aesthetics' if key == 'aesthetic' else key)
                    for val in dna.get(key, []):
                        stats[target_key][val] = stats[target_key].get(val, 0) + weight
            except: pass
            
    # Format and sort
    result = {}
    for key in stats:
        sorted_items = sorted(stats[key].items(), key=lambda x: x[1], reverse=True)
        # For talent, we only want those with significant presence
        limit = 15 if key != 'talent' else 20
        result[key] = [{'name': item[0], 'count': round(item[1], 1)} for item in sorted_items if item[1] > (0.3 if key != 'talent' else 0.5)][:limit]
        
    return result

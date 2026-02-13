from utils.analyzer import get_top_people, get_genre_stats

def get_user_taste_profile():
    """
    Aggregates the user's preferences into a weight map.
    """
    top_people = get_top_people(limit=50)
    genre_stats = get_genre_stats()
    
    # Map for quick lookup
    people_weights = {p['name']: p['count'] for p in top_people}
    
    # Normalize genre weights (0 to 40 points)
    if genre_stats:
        max_genre_count = max(g['count'] for g in genre_stats)
        genre_weights = {g['name']: (g['count'] / max_genre_count) * 40 for g in genre_stats}
    else:
        genre_weights = {}
        
    return {
        'people': people_weights,
        'genres': genre_weights
    }

def calculate_match_score(media_data, profile):
    """
    Scores a piece of media (from OMDb or DB) against the taste profile.
    media_data should have: 'Actors', 'Director', 'Writer', 'Genre', 'imdbRating'
    """
    score = 0
    details = []
    
    # 1. Score People
    people_in_media = []
    for key in ['Actors', 'Director', 'Writer']:
        val = media_data.get(key, '')
        if val and val != 'N/A':
            people_in_media.extend([p.split(' (')[0].strip() for p in val.split(', ')])
            
    for person in set(people_in_media):
        if person in profile['people']:
            count = profile['people'][person]
            points = 10 if count > 5 else 5
            score += points
            details.append(f"Matched {person} (+{points})")
            
    # 2. Score Genres
    genres = media_data.get('Genre', '').split(', ')
    genre_score = 0
    for genre in genres:
        if genre in profile['genres']:
            points = round(profile['genres'][genre], 1)
            genre_score += points
            
    # Cap genre score contribution to 40
    genre_score = min(genre_score, 40)
    if genre_score > 0:
        score += genre_score
        details.append(f"Genre Match (+{genre_score})")
        
    # 3. Add IMDb Rating (up to 10 points)
    try:
        rating = float(media_data.get('imdbRating', 0))
        score += rating
        details.append(f"IMDb Rating (+{rating})")
    except:
        pass
        
    return {
        'total_score': round(score, 1),
        'breakdown': details
    }

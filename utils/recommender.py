from utils.analyzer import get_top_people, get_genre_stats
from models import Media, MediaPerson, Person
from database import db

def get_user_taste_profile():
    """
    Aggregates the user's preferences into a weight map.
    Includes bonuses for user-rated (thumbs up/down) media.
    """
    top_people = get_top_people(limit=100)
    genre_stats = get_genre_stats()
    
    # Get people the user explicitly liked (thumbs up)
    liked_people_ids = db.session.query(MediaPerson.person_id).join(Media).filter(Media.user_rating == 1).distinct().all()
    liked_people_ids = [p[0] for p in liked_people_ids]

    # Get people the user explicitly disliked (thumbs down)
    disliked_people_ids = db.session.query(MediaPerson.person_id).join(Media).filter(Media.user_rating == -1).distinct().all()
    disliked_people_ids = [p[0] for p in disliked_people_ids]

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
        'genres': genre_weights,
        'liked_people_ids': liked_people_ids,
        'disliked_people_ids': disliked_people_ids
    }

def calculate_match_score(media_data, profile):
    """
    Scores a piece of media against the taste profile.
    """
    score = 0
    details = []
    
    # 1. Score People
    people_in_media = []
    for key in ['Actors', 'Director', 'Writer']:
        val = media_data.get(key, '')
        if val and val != 'N/A':
            people_in_media.extend([p.split(' (')[0].strip() for p in val.split(', ')])
            
    for person_name in set(people_in_media):
        # We need to find the person's ID to check explicit likes/dislikes
        person_obj = Person.query.filter_by(name=person_name).first()
        
        if person_obj:
            if person_obj.id in profile['disliked_people_ids']:
                score -= 20
                details.append(f"Contains {person_name} (Disliked Talent) (-20)")
                continue # Skip positive points
            
            if person_obj.id in profile['liked_people_ids']:
                score += 20
                details.append(f"Contains {person_name} (Liked Talent) (+20)")
            
        if person_name in profile['people']:
            count = profile['people'][person_name]
            points = 10 if count > 5 else 5
            score += points
            details.append(f"Matched {person_name} (+{points})")
            
    # 2. Score Genres
    genres = media_data.get('Genre', '').split(', ')
    genre_score = 0
    for genre in genres:
        if genre in profile['genres']:
            points = round(profile['genres'][genre], 1)
            genre_score += points
            
    genre_score = min(genre_score, 40)
    if genre_score > 0:
        score += genre_score
        details.append(f"Genre Match (+{genre_score})")
        
    # 3. Add IMDb Rating
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

def get_proactive_suggestions(db_instance, limit=5):
    """
    Finds new media suggestions by searching for works of top talent
    that aren't in the user's history.
    """
    from utils.omdb import OMDBClient
    from models import Media
    
    profile = get_user_taste_profile()
    # Get top 3 people by show count
    top_talent = sorted(profile['people'].items(), key=lambda x: x[1], reverse=True)[:3]
    
    client = OMDBClient()
    suggestions = []
    seen_titles = set([m.title.lower() for m in db_instance.session.query(Media.title).all()])
    
    for person, count in top_talent:
        # Search OMDb for this person (using them as a search term)
        # Note: OMDb search 's' returns a list, but 't' returns one. 
        # We'll use the search endpoint for candidates.
        params = {'apikey': client.api_key, 's': person, 'type': 'movie'}
        try:
            res = requests.get(client.base_url, params=params)
            data = res.json()
            if data.get('Response') == 'True':
                for item in data.get('Search', []):
                    title = item.get('Title')
                    if title.lower() not in seen_titles:
                        # Get full details for scoring
                        full_data = client.search_by_title(title)
                        if full_data:
                            score_data = calculate_match_score(full_data, profile)
                            suggestions.append({
                                'title': full_data.get('Title'),
                                'year': full_data.get('Year'),
                                'genre': full_data.get('Genre'),
                                'poster': full_data.get('Poster'),
                                'match': score_data
                            })
                            seen_titles.add(title.lower())
                    if len(suggestions) >= limit: break
        except:
            continue
        if len(suggestions) >= limit: break
            
    # Sort by total score
    return sorted(suggestions, key=lambda x: x['match']['total_score'], reverse=True)[:limit]

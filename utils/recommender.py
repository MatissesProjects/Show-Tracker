import requests
from utils.analyzer import get_top_people, get_genre_stats
from models import Media, MediaPerson, Person
from database import db

def get_user_taste_profile():
    """Aggregates the user's preferences into a weight map."""
    top_people = get_top_people(limit=100)
    genre_stats = get_genre_stats()
    
    liked_people_ids = [p[0] for p in db.session.query(MediaPerson.person_id).join(Media).filter(Media.user_rating == 1).distinct().all()]
    disliked_people_ids = [p[0] for p in db.session.query(MediaPerson.person_id).join(Media).filter(Media.user_rating == -1).distinct().all()]

    people_weights = {p['name']: p['count'] for p in top_people}
    
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
    """Scores a piece of media against the taste profile."""
    score = 0
    details = []
    
    # Normalize keys (handles both OMDb and TVmaze formats)
    actors = media_data.get('Actors') or media_data.get('cast') or ''
    genres_str = media_data.get('Genre') or ', '.join(media_data.get('genres', [])) or ''
    rating = media_data.get('imdbRating') or (media_data.get('rating') or {}).get('average') or 0

    people_in_media = []
    if isinstance(actors, list):
        people_in_media = actors
    else:
        people_in_media = [p.split(' (')[0].strip() for p in actors.split(', ') if p]
            
    for person_name in set(people_in_media):
        person_obj = Person.query.filter_by(name=person_name).first()
        if person_obj:
            if person_obj.id in profile['disliked_people_ids']:
                score -= 20
                details.append(f"Contains {person_name} (Disliked Talent) (-20)")
                continue
            if person_obj.id in profile['liked_people_ids']:
                score += 20
                details.append(f"Contains {person_name} (Liked Talent) (+20)")
            
        if person_name in profile['people']:
            count = profile['people'][person_name]
            points = 10 if count > 5 else 5
            score += points
            details.append(f"Matched {person_name} (+{points})")
            
    genres = genres_str.split(', ')
    genre_score = 0
    for genre in genres:
        if genre in profile['genres']:
            points = round(profile['genres'][genre], 1)
            genre_score += points
            
    genre_score = min(genre_score, 40)
    if genre_score > 0:
        score += genre_score
        details.append(f"Genre Match (+{genre_score})")
        
    try:
        score += float(rating)
        details.append(f"Rating (+{rating})")
    except: pass
        
    return {'total_score': round(score, 1), 'breakdown': details}

def get_proactive_suggestions(db_instance, limit=6):
    """Finds new suggestions using TVmaze to search by top talent."""
    profile = get_user_taste_profile()
    # Get top 5 people
    top_talent = sorted(profile['people'].items(), key=lambda x: x[1], reverse=True)[:5]
    
    suggestions = []
    seen_titles = set([m.title.lower() for m in db_instance.session.query(Media.title).all()])
    
    for person_name, count in top_talent:
        # 1. Search for the person on TVmaze to get their ID
        person_res = requests.get(f"https://api.tvmaze.com/search/people?q={person_name}")
        if not person_res.ok or not person_res.json(): continue
        
        person_id = person_res.json()[0]['person']['id']
        
        # 2. Get their cast credits
        credits_res = requests.get(f"https://api.tvmaze.com/people/{person_id}/castcredits?embed=show")
        if not credits_res.ok: continue
        
        for credit in credits_res.json():
            show = credit['_embedded']['show']
            title = show['name']
            
            if title.lower() not in seen_titles:
                score_data = calculate_match_score(show, profile)
                suggestions.append({
                    'title': title,
                    'year': show.get('premiered', '')[:4],
                    'genre': ', '.join(show.get('genres', [])),
                    'poster': (show.get('image') or {}).get('medium'),
                    'match': score_data
                })
                seen_titles.add(title.lower())
                
            if len(suggestions) >= limit: break
        if len(suggestions) >= limit: break
            
    return sorted(suggestions, key=lambda x: x['match']['total_score'], reverse=True)[:limit]

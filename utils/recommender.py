import requests
import random
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
    
    # Normalize keys
    actors = media_data.get('Actors') or media_data.get('cast') or ''
    genres_list = media_data.get('genres', []) if isinstance(media_data.get('genres'), list) else (media_data.get('Genre', '').split(', ') if media_data.get('Genre') else [])
    rating = media_data.get('imdbRating') or (media_data.get('rating') or {}).get('average') or 0

    people_in_media = []
    if isinstance(actors, list):
        people_in_media = actors
    else:
        if '_embedded' in media_data and 'cast' in media_data['_embedded']:
            people_in_media = [c['person']['name'] for c in media_data['_embedded']['cast']]
        else:
            people_in_media = [p.split(' (')[0].strip() for p in actors.split(', ') if p]
            
    for person_name in set(people_in_media):
        person_obj = Person.query.filter_by(name=person_name).first()
        if person_obj:
            if person_obj.id in profile['disliked_people_ids']:
                score -= 40
                details.append(f"Disliked Talent: {person_name} (-40)")
                continue
            if person_obj.id in profile['liked_people_ids']:
                score += 30
                details.append(f"Liked Talent: {person_name} (+30)")
            
        if person_name in profile['people']:
            count = profile['people'][person_name]
            points = 15 if count > 5 else 8
            score += points
            details.append(f"Frequent Talent: {person_name} (+{points})")
            
    for genre in genres_list:
        if genre in profile['genres']:
            points = round(profile['genres'][genre], 1)
            score += points
            
    try:
        r_val = float(rating)
        score += r_val
        details.append(f"Rating (+{r_val})")
    except: pass
        
    return {'total_score': round(score, 1), 'breakdown': details}

def get_proactive_suggestions(db_instance, limit=20, target_people=None, target_genres=None):
    """
    Enhanced engine with multi-filter support.
    """
    profile = get_user_taste_profile()
    suggestions = []
    seen_titles = set([m.title.lower() for m in db_instance.session.query(Media.title).all()])
    
    search_people = target_people if target_people else []
    search_genres = target_genres if target_genres else []

    # Strategy 1: Filtered Search (Explicit selections)
    if search_people or search_genres:
        # Search by specific people
        for person_name in search_people:
            suggestions.extend(fetch_by_person(person_name, profile, seen_titles, limit))
        
        # Search by specific genres
        for genre_name in search_genres:
            suggestions.extend(fetch_by_genre(genre_name, profile, seen_titles, limit))
            
        # If we have both, only keep those that match BOTH where possible? 
        # For now, let's just return the combined set, sorted by score.
    else:
        # Auto-mode: pick from liked names or top talent
        liked_people = db_instance.session.query(Person.name).filter(Person.id.in_(profile['liked_people_ids'])).all()
        liked_names = [p[0] for p in liked_people]
        auto_search = liked_names if liked_names else sorted(profile['people'].items(), key=lambda x: x[1], reverse=True)[:15]
        if auto_search and isinstance(auto_search[0], tuple): auto_search = [p[0] for p in auto_search]
        random.shuffle(auto_search)
        
        for person_name in auto_search[:8]:
            suggestions.extend(fetch_by_person(person_name, profile, seen_titles, limit))
            if len(suggestions) >= limit: break

    # Remove duplicates and sort by match score
    unique_suggestions = {s['title']: s for s in suggestions}.values()
    return sorted(unique_suggestions, key=lambda x: x['match']['total_score'], reverse=True)[:limit]

def fetch_by_person(person_name, profile, seen_titles, limit):
    results = []
    try:
        person_res = requests.get(f"https://api.tvmaze.com/search/people?q={person_name}", timeout=5)
        if person_res.ok and person_res.json():
            person_id = person_res.json()[0]['person']['id']
            credits_res = requests.get(f"https://api.tvmaze.com/people/{person_id}/castcredits?embed=show", timeout=5)
            if credits_res.ok:
                for credit in credits_res.json():
                    show = credit['_embedded']['show']
                    if show['name'].lower() not in seen_titles:
                        show['cast'] = [person_name]
                        score_data = calculate_match_score(show, profile)
                        results.append(format_suggestion(show, score_data))
                        seen_titles.add(show['name'].lower())
                    if len(results) >= limit: break
    except: pass
    return results

def fetch_by_genre(genre_name, profile, seen_titles, limit):
    results = []
    try:
        genre_res = requests.get(f"https://api.tvmaze.com/search/shows?q={genre_name}", timeout=5)
        if genre_res.ok:
            for item in genre_res.json():
                show = item['show']
                if show['name'].lower() not in seen_titles:
                    score_data = calculate_match_score(show, profile)
                    results.append(format_suggestion(show, score_data))
                    seen_titles.add(show['name'].lower())
                if len(results) >= limit: break
    except: pass
    return results

def format_suggestion(show, score_data):
    network = (show.get('network') or {}).get('name', '')
    web_channel = (show.get('webChannel') or {}).get('name', '')
    return {
        'title': show['name'],
        'year': show.get('premiered', '')[:4],
        'genre': ', '.join(show.get('genres', [])),
        'poster': (show.get('image') or {}).get('medium'),
        'match': score_data,
        'on_netflix': 'Netflix' in [network, web_channel],
        'summary': (show.get('summary') or '').replace('<p>', '').replace('</p>', '').strip()
    }

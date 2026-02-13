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

def get_proactive_suggestions(db_instance, limit=20, target_person=None, target_genre=None):
    """
    Enhanced engine with filtering for specific talent or genres.
    """
    profile = get_user_taste_profile()
    suggestions = []
    seen_titles = set([m.title.lower() for m in db_instance.session.query(Media.title).all()])
    
    search_terms = []
    if target_person:
        search_terms = [target_person]
    elif target_genre:
        # TVmaze doesn't have a direct genre endpoint, we search for shows with that keyword
        try:
            genre_res = requests.get(f"https://api.tvmaze.com/search/shows?q={target_genre}", timeout=5)
            if genre_res.ok:
                for item in genre_res.json():
                    show = item['show']
                    title = show['name']
                    if title.lower() not in seen_titles:
                        score_data = calculate_match_score(show, profile)
                        suggestions.append(format_suggestion(show, score_data))
                        seen_titles.add(title.lower())
                    if len(suggestions) >= limit: return suggestions
        except: pass
        return suggestions

    else:
        # Auto-mode: pick from liked names or top talent
        liked_people = db_instance.session.query(Person.name).filter(Person.id.in_(profile['liked_people_ids'])).all()
        liked_names = [p[0] for p in liked_people]
        search_terms = liked_names if liked_names else sorted(profile['people'].items(), key=lambda x: x[1], reverse=True)[:15]
        if search_terms and isinstance(search_terms[0], tuple): search_terms = [p[0] for p in search_terms]
        random.shuffle(search_terms)

    for person_name in search_terms[:8]:
        try:
            person_res = requests.get(f"https://api.tvmaze.com/search/people?q={person_name}", timeout=5)
            if not person_res.ok or not person_res.json(): continue
            
            person_id = person_res.json()[0]['person']['id']
            credits_res = requests.get(f"https://api.tvmaze.com/people/{person_id}/castcredits?embed=show", timeout=5)
            if not credits_res.ok: continue
            
            credits = credits_res.json()
            random.shuffle(credits)

            for credit in credits:
                show = credit['_embedded']['show']
                title = show['name']
                if title.lower() not in seen_titles:
                    show['cast'] = [person_name]
                    score_data = calculate_match_score(show, profile)
                    suggestions.append(format_suggestion(show, score_data))
                    seen_titles.add(title.lower())
                if len(suggestions) >= limit: break
        except: continue
        if len(suggestions) >= limit: break

    return sorted(suggestions, key=lambda x: x['match']['total_score'], reverse=True)

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

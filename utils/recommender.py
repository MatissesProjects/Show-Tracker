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
        # Check for TVmaze embedded cast
        if '_embedded' in media_data and 'cast' in media_data['_embedded']:
            people_in_media = [c['person']['name'] for c in media_data['_embedded']['cast']]
        else:
            people_in_media = [p.split(' (')[0].strip() for p in actors.split(', ') if p]
            
    for person_name in set(people_in_media):
        person_obj = Person.query.filter_by(name=person_name).first()
        if person_obj:
            if person_obj.id in profile['disliked_people_ids']:
                score -= 30
                details.append(f"Contains {person_name} (Disliked Talent) (-30)")
                continue
            if person_obj.id in profile['liked_people_ids']:
                score += 25
                details.append(f"Contains {person_name} (Liked Talent) (+25)")
            
        if person_name in profile['people']:
            count = profile['people'][person_name]
            points = 15 if count > 5 else 8
            score += points
            details.append(f"Matched {person_name} (+{points})")
            
    genres = genres_str.split(', ')
    genre_score = 0
    for genre in genres:
        if genre in profile['genres']:
            points = round(profile['genres'][genre], 1)
            genre_score += points
            
    genre_score = min(genre_score, 45)
    if genre_score > 0:
        score += genre_score
        details.append(f"Genre Match (+{genre_score})")
        
    try:
        r_val = float(rating)
        score += r_val
        details.append(f"Rating (+{r_val})")
    except: pass
        
    return {'total_score': round(score, 1), 'breakdown': details}

def get_proactive_suggestions(db_instance, limit=15):
    """Finds more diverse suggestions using TVmaze."""
    profile = get_user_taste_profile()
    top_talent = sorted(profile['people'].items(), key=lambda x: x[1], reverse=True)[:8]
    
    suggestions = []
    seen_titles = set([m.title.lower() for m in db_instance.session.query(Media.title).all()])
    
    for person_name, count in top_talent:
        person_res = requests.get(f"https://api.tvmaze.com/search/people?q={person_name}")
        if not person_res.ok or not person_res.json(): continue
        
        person_id = person_res.json()[0]['person']['id']
        credits_res = requests.get(f"https://api.tvmaze.com/people/{person_id}/castcredits?embed=show")
        if not credits_res.ok: continue
        
        for credit in credits_res.json():
            show = credit['_embedded']['show']
            title = show['name']
            
            if title.lower() not in seen_titles:
                # Add cast to show data for better scoring
                show['cast'] = [person_name] 
                score_data = calculate_match_score(show, profile)
                
                suggestions.append({
                    'title': title,
                    'year': show.get('premiered', '')[:4],
                    'genre': ', '.join(show.get('genres', [])),
                    'poster': (show.get('image') or {}).get('medium'),
                    'match': score_data,
                    'summary': show.get('summary', '').replace('<p>', '').replace('</p>', '').replace('<b>', '').replace('</b>', '')
                })
                seen_titles.add(title.lower())
                
            if len(suggestions) >= limit: break
        if len(suggestions) >= limit: break
            
    return sorted(suggestions, key=lambda x: x['match']['total_score'], reverse=True)

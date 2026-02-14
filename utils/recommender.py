import requests
import random
from utils.analyzer import get_top_people, get_genre_stats
from models import Media, MediaPerson, Person
from database import db

def get_user_taste_profile():
    """Aggregates the user's preferences into a high-fidelity weight map."""
    top_people = get_top_people(limit=100)
    genre_stats = get_genre_stats()
    
    # Tiered weight identification
    loved_media = Media.query.filter(Media.user_rating == 2).all()
    liked_media = Media.query.filter(Media.user_rating == 1).all()
    
    loved_people_ids = [p[0] for p in db.session.query(MediaPerson.person_id).join(Media).filter(Media.user_rating == 2).distinct().all()]
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
        'loved_people_ids': loved_people_ids,
        'liked_people_ids': liked_people_ids,
        'disliked_people_ids': disliked_people_ids,
        'loved_media': loved_media,
        'liked_media': liked_media
    }

def calculate_match_score(media_data, profile):
    """Enhanced scoring with tiered weights and Creator/Director awareness."""
    score = 0
    details = []
    
    actors = media_data.get('Actors') or media_data.get('cast') or ''
    director = media_data.get('Director') or ''
    writer = media_data.get('Writer') or ''
    genres_list = media_data.get('genres', []) if isinstance(media_data.get('genres'), list) else (media_data.get('Genre', '').split(', ') if media_data.get('Genre') else [])
    rating = media_data.get('imdbRating') or (media_data.get('rating') or {}).get('average') or 0

    # Talent & Creator Pool
    talent_pool = []
    if isinstance(actors, list): talent_pool.extend(actors)
    else:
        if '_embedded' in media_data and 'cast' in media_data['_embedded']:
            talent_pool.extend([c['person']['name'] for c in media_data['_embedded']['cast']])
        else:
            talent_pool.extend([p.split(' (')[0].strip() for p in actors.split(', ') if p])
    
    # Add Creators
    talent_pool.extend([p.strip() for p in director.split(',') if p])
    talent_pool.extend([p.strip() for p in writer.split(',') if p])

    for person_name in set(talent_pool):
        person_obj = Person.query.filter_by(name=person_name).first()
        if person_obj:
            if person_obj.id in profile['disliked_people_ids']:
                score -= 60
                details.append(f"Avoid: {person_name} (Disliked) (-60)")
                continue
            
            if person_obj.id in profile['loved_people_ids']:
                score += 80
                details.append(f"Starring/Created by {person_name} (LOVED) (+80)")
            elif person_obj.id in profile['liked_people_ids']:
                score += 40
                details.append(f"Starring/Created by {person_name} (Liked) (+40)")

        if person_name in profile['people']:
            count = profile['people'][person_name]
            points = 25 if count > 5 else 12
            score += points
            details.append(f"Frequent Talent: {person_name} (+{points})")
    genre_match_count = 0
    for genre in genres_list:
        if genre in profile['genres']:
            score += round(profile['genres'][genre], 1)
            genre_match_count += 1
    if genre_match_count > 0:
        details.append(f"Matched {genre_match_count} Preferred Genres")
    try:
        r_val = float(rating)
        if r_val > 8.0:
            score += 15
            details.append(f"Highly Rated ({r_val}) (+15)")
        elif r_val > 7.0:
            score += 10
            details.append(f"Well Rated ({r_val}) (+10)")
        else:
            score += r_val
    except: pass
    return {'total_score': round(score, 1), 'breakdown': details}

from utils.cache import get_cached_response, set_cached_response
import time

def get_proactive_suggestions(db_instance, limit=20, target_people=None, target_genres=None, refresh=False):
    # Generate a key based on params
    params_key = f"suggestions_{target_people}_{target_genres}"
    
    # Return cache if less than 1 hour old, UNLESS refresh is requested
    if not refresh:
        cached = get_cached_response(params_key, expiry_days=0.04) # ~1 hour
        if cached:
            return cached

    profile = get_user_taste_profile()
    suggestions = []
    seen_titles = set([m.title.lower() for m in db_instance.session.query(Media.title).all()])
    
    # Use a session for faster repeated requests
    session = requests.Session()
    
    if target_people or target_genres:
        # 1. Fetch filtered results
        for p in (target_people or []): 
            suggestions.extend(fetch_by_person(p, profile, seen_titles, limit, session))
        for g in (target_genres or []): 
            suggestions.extend(fetch_by_genre(g, profile, seen_titles, limit, session))
            
        # 2. If we have few results, supplement with general intelligence
        if len(suggestions) < 5:
            supplemental = get_general_intelligence_suggestions(db_instance, profile, seen_titles, limit // 2, session)
            suggestions.extend(supplemental)
    else:
        suggestions = get_general_intelligence_suggestions(db_instance, profile, seen_titles, limit, session)

    unique_suggestions = {s['title']: s for s in suggestions if s.get('poster')}.values()
    high_quality = [s for s in unique_suggestions if s['match']['total_score'] > 20]
    result = sorted(high_quality if high_quality else unique_suggestions, key=lambda x: x['match']['total_score'], reverse=True)[:limit]
    
    # Store in cache
    set_cached_response(params_key, result)
    
    return result

def get_general_intelligence_suggestions(db_instance, profile, seen_titles, limit, session=None):
    """Fallback/General strategy using user DNA."""
    if session is None: session = requests.Session()
    suggestions = []
    
    # Strategy A: Similarity via 'Loved' & 'Liked' Media DNA
    dna_sample_pool = profile['loved_media'] + profile['liked_media']
    if dna_sample_pool:
        sample_size = min(len(dna_sample_pool), 8)
        sample_likes = random.sample(dna_sample_pool, sample_size)
        for media in sample_likes:
            # Get up to 2 actors per show
            actors = [mp.person.name for mp in media.person_memberships if mp.role == 'Actor'][:2]
            genres = (media.genres or "").split(', ')
            for actor in actors:
                candidates = fetch_by_person(actor, profile, seen_titles, 3, session)
                for c in candidates:
                    c_genres = c['genre'].split(', ')
                    if any(g in c_genres for g in genres):
                        boost = 40 if media.user_rating == 2 else 20
                        c['match']['total_score'] += boost
                        c['match']['breakdown'].insert(0, f"DNA Similarity to {media.title} (+{boost})")
                        suggestions.append(c)
    
    # Strategy B: Top Talent rotation
    top_talent = sorted(profile['people'].items(), key=lambda x: x[1], reverse=True)[:10]
    random.shuffle(top_talent)
    for person_name, count in top_talent[:3]: 
        suggestions.extend(fetch_by_person(person_name, profile, seen_titles, 5, session))
        
    return suggestions

def fetch_by_person(person_name, profile, seen_titles, limit, session=None):
    if session is None: session = requests.Session()
    
    cache_key = f"tvmaze_person_{person_name.lower().replace(' ', '_')}"
    cached_person_id = get_cached_response(cache_key)
    
    results = []
    try:
        person_id = None
        if cached_person_id:
            person_id = cached_person_id
        else:
            person_res = session.get(f"https://api.tvmaze.com/search/people?q={requests.utils.quote(person_name)}", timeout=5)
            if person_res.ok and person_res.json():
                person_id = person_res.json()[0]['person']['id']
                set_cached_response(cache_key, person_id)

        if person_id:
            # Check credits cache
            credits_cache_key = f"tvmaze_credits_{person_id}"
            cached_credits = get_cached_response(credits_cache_key, expiry_days=7)
            
            credits_data = []
            if cached_credits:
                credits_data = cached_credits
            else:
                # 1. Fetch Cast Credits
                cast_res = session.get(f"https://api.tvmaze.com/people/{person_id}/castcredits?embed=show", timeout=5)
                if cast_res.ok:
                    credits_data.extend(cast_res.json())
                
                # 2. Fetch Crew Credits (Directors, Creators)
                crew_res = session.get(f"https://api.tvmaze.com/people/{person_id}/crewcredits?embed=show", timeout=5)
                if crew_res.ok:
                    credits_data.extend(crew_res.json())
                
                set_cached_response(credits_cache_key, credits_data)

            for credit in credits_data:
                show = credit.get('_embedded', {}).get('show')
                if not show: continue
                title_low = show['name'].lower()
                if title_low not in seen_titles:
                    show['cast'] = [person_name]
                    score_data = calculate_match_score(show, profile)
                    results.append(format_suggestion(show, score_data))
                    seen_titles.add(title_low)
                if len(results) >= limit: break
    except Exception as e:
        print(f"Error fetching for {person_name}: {e}")
    return results

def fetch_by_genre(genre_name, profile, seen_titles, limit, session=None):
    if session is None: session = requests.Session()
    
    cache_key = f"tvmaze_genre_{genre_name.lower()}"
    cached = get_cached_response(cache_key, expiry_days=7)
    
    results = []
    try:
        genre_data = []
        if cached:
            genre_data = cached
        else:
            genre_res = session.get(f"https://api.tvmaze.com/search/shows?q={requests.utils.quote(genre_name)}", timeout=5)
            if genre_res.ok:
                genre_data = genre_res.json()
                set_cached_response(cache_key, genre_data)

        for item in genre_data:
            show = item['show']
            title_low = show['name'].lower()
            if title_low not in seen_titles:
                score_data = calculate_match_score(show, profile)
                results.append(format_suggestion(show, score_data))
                seen_titles.add(title_low)
            if len(results) >= limit: break
    except: pass
    return results

def format_suggestion(show, score_data):
    network = (show.get('network') or {}).get('name', '')
    web_channel = (show.get('webChannel') or {}).get('name', '')
    title = show['name']
    return {
        'title': title,
        'year': show.get('premiered', '')[:4],
        'media_type': 'series',
        'genre': ', '.join(show.get('genres', [])),
        'runtime': f"{show.get('runtime', '')} min" if show.get('runtime') else None,
        'total_seasons': None, # TVMaze doesn't provide this in the search response easily
        'poster': (show.get('image') or {}).get('medium'),
        'match': score_data,
        'on_netflix': 'Netflix' in [network, web_channel],
        'summary': (show.get('summary') or '').replace('<p>', '').replace('</p>', '').replace('<b>', '').replace('</b>', '').strip(),
        'youtube_url': f"https://www.youtube.com/results?search_query={title.replace(' ', '+')}+funny+moments+clips"
    }

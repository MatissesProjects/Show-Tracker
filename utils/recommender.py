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

def get_proactive_suggestions(db_instance, limit=20, target_people=None, target_genres=None):
    profile = get_user_taste_profile()
    suggestions = []
    seen_titles = set([m.title.lower() for m in db_instance.session.query(Media.title).all()])
    if target_people or target_genres:
        for p in (target_people or []): suggestions.extend(fetch_by_person(p, profile, seen_titles, limit))
        for g in (target_genres or []): suggestions.extend(fetch_by_genre(g, profile, seen_titles, limit))
    else:
        # Strategy A: Similarity via 'Loved' & 'Liked' Media DNA
        # Prioritize loved items for the sample if available
        dna_sample_pool = profile['loved_media'] + profile['liked_media']
        if dna_sample_pool:
            sample_likes = random.sample(dna_sample_pool, min(len(dna_sample_pool), 8))
            for media in sample_likes:
                actors = [mp.person.name for mp in media.person_memberships if mp.role == 'Actor'][:3]
                genres = (media.genres or "").split(', ')
                for actor in actors:
                    candidates = fetch_by_person(actor, profile, seen_titles, 5)
                    for c in candidates:
                        c_genres = c['genre'].split(', ')
                        if any(g in c_genres for g in genres):
                            # Boost based on whether the DNA source was loved or liked
                            boost = 40 if media.user_rating == 2 else 20
                            c['match']['total_score'] += boost
                            c['match']['breakdown'].insert(0, f"DNA Similarity to {media.title} (+{boost})")
                            suggestions.append(c)
        top_talent = sorted(profile['people'].items(), key=lambda x: x[1], reverse=True)[:10]
        random.shuffle(top_talent)
        for person_name, count in top_talent[:5]: suggestions.extend(fetch_by_person(person_name, profile, seen_titles, 5))
    unique_suggestions = {s['title']: s for s in suggestions if s['poster']}.values()
    high_quality = [s for s in unique_suggestions if s['match']['total_score'] > 30]
    return sorted(high_quality if high_quality else unique_suggestions, key=lambda x: x['match']['total_score'], reverse=True)[:limit]

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
    title = show['name']
    return {
        'title': title,
        'year': show.get('premiered', '')[:4],
        'genre': ', '.join(show.get('genres', [])),
        'poster': (show.get('image') or {}).get('medium'),
        'match': score_data,
        'on_netflix': 'Netflix' in [network, web_channel],
        'summary': (show.get('summary') or '').replace('<p>', '').replace('</p>', '').replace('<b>', '').replace('</b>', '').strip(),
        'youtube_url': f"https://www.youtube.com/results?search_query={title.replace(' ', '+')}+funny+moments+clips"
    }

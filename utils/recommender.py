import requests
import random
from models import Media, MediaPerson, Person, WatchHistory
from database import db

def get_user_taste_profile(refresh=False):
    """Aggregates the user's preferences with weighted importance for rated items."""
    cache_key = "user_taste_dna_v1"
    if not refresh:
        cached = get_cached_response(cache_key, expiry_days=0.5) # 12 hour cache
        if cached:
            # Convert lists back to sets/objects if necessary, 
            # though here we mainly return dicts of scores.
            return cached

    # Fetch all watched media to calculate refined weights
    watched_media = Media.query.join(WatchHistory).distinct().all()
    
    people_scores = {}
    genre_scores = {}
    theme_scores = {}
    mood_scores = {}
    aesthetic_scores = {}
    
    import json
    for media in watched_media:
        # Weight: 1.0 for Loved (2), 0.7 for Liked (1), 0.2 for Unrated (0)
        weight = 0.2
        if media.user_rating == 2: weight = 1.0
        elif media.user_rating == 1: weight = 0.7
        elif media.user_rating == -1: continue 
        
        # Talent & Genres (existing)
        for mp in media.person_memberships:
            name = mp.person.name
            people_scores[name] = people_scores.get(name, 0) + weight
        if media.genres:
            genres = media.genres.split(', ')
            for g in genres:
                genre_scores[g] = genre_scores.get(g, 0) + weight
                
        # Thematic DNA (New)
        if media.thematic_metadata:
            try:
                dna = json.loads(media.thematic_metadata)
                for key in ['themes', 'mood', 'aesthetic', 'tropes']:
                    target_key = 'moods' if key == 'mood' else ('aesthetics' if key == 'aesthetic' else key)
                    for val in dna.get(key, []):
                        stats = theme_scores if target_key == 'themes' else (mood_scores if target_key == 'moods' else aesthetic_scores)
                        # Tropes are handled as themes for scoring
                        if target_key == 'tropes': stats = theme_scores
                        stats[val] = stats.get(val, 0) + weight
            except: pass

    # Tiered weight identification for explicit matching (Names instead of IDs for speed)
    loved_titles = [m.title for m in watched_media if m.user_rating == 2]
    liked_titles = [m.title for m in watched_media if m.user_rating == 1]
    loved_people = [p[0] for p in db.session.query(Person.name).join(MediaPerson).join(Media).filter(Media.user_rating == 2).distinct().all()]
    liked_people = [p[0] for p in db.session.query(Person.name).join(MediaPerson).join(Media).filter(Media.user_rating == 1).distinct().all()]
    disliked_people = [p[0] for p in db.session.query(Person.name).join(MediaPerson).join(Media).filter(Media.user_rating == -1).distinct().all()]

    if genre_scores:
        max_genre_score = max(genre_scores.values())
        genre_weights = {name: (score / max_genre_score) * 40 for name, score in genre_scores.items()}
    else:
        genre_weights = {}
        
    result = {
        'people': people_scores,
        'genres': genre_weights,
        'themes': theme_scores,
        'moods': mood_scores,
        'aesthetics': aesthetic_scores,
        'loved_titles': loved_titles,
        'liked_titles': liked_titles,
        'loved_people': loved_people,
        'liked_people': liked_people,
        'disliked_people': disliked_people
    }
    
    set_cached_response(cache_key, result)
    return result

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
    
    # Add Creators/Directors
    talent_pool.extend([p.strip() for p in director.split(',') if p])
    talent_pool.extend([p.strip() for p in writer.split(',') if p])

    # Pre-convert to sets for O(1) lookups
    loved_set = set(profile.get('loved_people', []))
    liked_set = set(profile.get('liked_people', []))
    disliked_set = set(profile.get('disliked_people', []))

    for person_name in set(talent_pool):
        if person_name in disliked_set:
            score -= 100 # Heavily penalize dislikes
            details.append(f"Avoid: {person_name} (Disliked) (-100)")
            continue
        
        if person_name in loved_set:
            score += 120 # Massive boost for loved creators/actors
            details.append(f"Starring/Created by {person_name} (LOVED) (+120)")
        elif person_name in liked_set:
            score += 50
            details.append(f"Starring/Created by {person_name} (Liked) (+50)")

        if person_name in profile['people']:
            weighted_count = profile['people'][person_name]
            # Higher reward for talent you've explicitly rated/liked multiple times
            if weighted_count > 3:
                points = 40
            elif weighted_count > 1:
                points = 20
            else:
                points = 10
            score += points
            details.append(f"Frequent Talent: {person_name} (Weighted: {round(weighted_count, 1)}) (+{points})")

    # Genre Affinity
    genre_match_count = 0
    for genre in genres_list:
        if genre in profile['genres']:
            weight = profile['genres'][genre]
            score += round(weight, 1)
            genre_match_count += 1
            if weight > 30: # Top tier genre
                score += 10 # Bonus for high-affinity genre
    
    if genre_match_count > 0:
        details.append(f"Matched {genre_match_count} Preferred Genres")

    # Thematic DNA Matching (New)
    # Since we can't extract DNA for every suggestion instantly without killing API,
    # we use a "DNA Similarity" strategy if the suggestion already has DNA cached.
    # If not, the "Thematic AI Discovery" strategy in get_proactive_suggestions handles it.
    
    # Check if this item has cached DNA (via APICache or it's a known Media item)
    cache_key = f"ai_dna_{media_data.get('Title', '').lower().replace(' ', '_')}"
    cached_dna = get_cached_response(cache_key)
    if cached_dna:
        dna_score = 0
        matches = []
        for t in cached_dna.get('themes', []):
            if t in profile['themes']:
                dna_score += 15
                matches.append(t)
        for m in cached_dna.get('mood', []):
            if m in profile['moods']:
                dna_score += 10
                matches.append(m)
        for a in cached_dna.get('aesthetic', []):
            if a in profile['aesthetics']:
                dna_score += 10
                matches.append(a)
        
        if dna_score > 0:
            score += dna_score
            details.append(f"DNA Match: {', '.join(matches[:3])} (+{dna_score})")

    # Quality Signal
    try:
        r_val = float(rating)
        if r_val > 8.5:
            score += 40 # Masterpiece boost
            details.append(f"Top-Tier Rating ({r_val}) (+40)")
        elif r_val > 7.5:
            score += 20
            details.append(f"Solid Rating ({r_val}) (+20)")
        elif r_val < 5.0 and r_val > 0:
            score -= 30
            details.append(f"Poorly Rated ({r_val}) (-30)")
    except: pass
    
    return {'total_score': round(score, 1), 'breakdown': details}

from utils.cache import get_cached_response, set_cached_response
import time

def get_proactive_suggestions(db_instance, limit=20, target_people=None, target_genres=None, 
                              target_themes=None, target_moods=None, target_aesthetics=None,
                              refresh=False):
    # Generate a key based on params
    params_key = f"suggestions_v3_{target_people}_{target_genres}_{target_themes}_{target_moods}_{target_aesthetics}"
    
    # Return cache if less than 2 hours old, UNLESS refresh is requested
    if not refresh:
        cached = get_cached_response(params_key, expiry_days=0.08) # ~2 hours
        if cached:
            return cached

    profile = get_user_taste_profile()
    suggestions = []
    seen_titles = set([m.title.lower() for m in db_instance.session.query(Media.title).all()])
    
    # Use a session for faster repeated requests
    session = requests.Session()
    
    # Strategy A: Direct Filtering (User Requested)
    if any([target_people, target_genres, target_themes, target_moods, target_aesthetics]):
        for p in (target_people or []): 
            suggestions.extend(fetch_by_person(p, profile, seen_titles, limit, session))
        for g in (target_genres or []): 
            suggestions.extend(fetch_by_genre(g, profile, seen_titles, limit, session))
            
        # Thematic filtering requires AI brainstorming for candidates since TVMaze doesn't have themes
        thematic_queries = (target_themes or []) + (target_moods or []) + (target_aesthetics or [])
        for query in thematic_queries:
            suggestions.extend(fetch_by_thematic_discovery(query, profile, seen_titles, session))
            
    # Strategy B: AI-Powered Thematic Brainstorming (NEW)
    # This finds titles that aren't just direct actor/genre matches but share "Vibe DNA"
    ai_candidates = get_ai_thematic_candidates(profile, seen_titles)
    for title in ai_candidates:
        data = fetch_by_title_tvmaze(title, profile, seen_titles, session)
        if data:
            data['match']['total_score'] += 30 # AI Recommendation Boost
            data['match']['breakdown'].insert(0, "Thematic AI Discovery (+30)")
            suggestions.append(data)

    # Strategy C: Top Talent & DNA Similarity (Existing)
    if len(suggestions) < limit:
        supplemental = get_general_intelligence_suggestions(db_instance, profile, seen_titles, limit, session)
        suggestions.extend(supplemental)

    unique_suggestions = {s['title']: s for s in suggestions if s.get('poster')}.values()
    
    # Refined Scoring: Penalize obvious/over-suggested items, reward high match depth
    result = sorted(unique_suggestions, key=lambda x: x['match']['total_score'], reverse=True)[:limit]
    
    # Store in cache
    set_cached_response(params_key, result)
    
    return result

def get_ai_thematic_candidates(profile, seen_titles):
    """Uses the AI Analyst to brainstorm 10 high-potential titles based on deep taste DNA."""
    from utils.ai_analyst import AIAnalyst
    analyst = AIAnalyst()
    if not analyst.check_availability():
        return []

    loved = profile.get('loved_titles', [])[:10]
    genres = list(profile['genres'].keys())[:5]
    
    prompt = f"""
    [TASTE PROFILE]
    Loved Shows/Movies: {', '.join(loved)}
    Preferred Genres: {', '.join(genres)}
    
    [TASK]
    Brainstorm 10 'Thematic Siblings'—media that shares the same tone, writing style, or philosophical themes as the loved list. 
    Exclude these already watched titles: {', '.join(list(seen_titles)[:20])}
    
    Output ONLY a JSON list of titles. No commentary.
    Example: ["Title 1", "Title 2"]
    """
    
    try:
        import re, json
        response = analyst.chat_with_library(prompt, [])
        match = re.search(r'\[\s*".*"\s*\]', response, re.DOTALL)
        if match:
            return json.loads(match.group())
        return re.findall(r'"([^"]*)"', response)
    except:
        return []

def fetch_by_thematic_discovery(query, profile, seen_titles, session=None):
    """Uses AI to find candidates for a specific theme/mood/aesthetic."""
    from utils.ai_analyst import AIAnalyst
    analyst = AIAnalyst()
    if not analyst.check_availability():
        return []
        
    prompt = f"Suggest 5 TV shows or movies that perfectly embody the DNA of '{query}'. Output ONLY a JSON list of titles."
    
    results = []
    try:
        import re, json
        response = analyst.chat_with_library(prompt, [])
        match = re.search(r'\[\s*".*"\s*\]', response, re.DOTALL)
        titles = json.loads(match.group()) if match else re.findall(r'"([^"]*)"', response)
        
        for title in titles:
            data = fetch_by_title_tvmaze(title, profile, seen_titles, session)
            if data:
                data['match']['total_score'] += 20
                data['match']['breakdown'].append(f"Thematic match for '{query}' (+20)")
                results.append(data)
    except: pass
    return results

def fetch_by_title_tvmaze(title, profile, seen_titles, session=None):
    """Specific fetcher for a single title."""
    if session is None: session = requests.Session()
    try:
        res = session.get(f"https://api.tvmaze.com/singlesearch/shows?q={requests.utils.quote(title)}", timeout=5)
        if res.ok:
            show = res.json()
            title_low = show['name'].lower()
            if title_low not in seen_titles:
                score_data = calculate_match_score(show, profile)
                seen_titles.add(title_low)
                return format_suggestion(show, score_data)
    except: pass
    return None

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

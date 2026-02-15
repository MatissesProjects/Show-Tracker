
from flask import Blueprint, jsonify, request
from database import db
from models import Media
from utils.ai_analyst import AIAnalyst
from utils.omdb import OMDBClient
from utils.recommender import get_user_taste_profile, calculate_match_score, get_proactive_suggestions
import json
import re

ai_bp = Blueprint('ai', __name__)

@ai_bp.route('/api/ai/status', methods=['GET'])
def ai_status():
    analyst = AIAnalyst()
    available = analyst.check_availability()
    return jsonify({'available': available}), 200

@ai_bp.route('/api/ai/deep-discovery', methods=['GET'])
def deep_discovery():
    refresh = request.args.get('refresh', 'false').lower() == 'true'
    profile = get_user_taste_profile()
    analyst = AIAnalyst()
    client = OMDBClient()
    
    all_tracked_titles = [m.title for m in Media.query.all()]
    
    context = {
        'loved': profile.get('loved_titles', []),
        'liked': profile.get('liked_titles', []),
        'talent': list(profile['people'].keys())[:10],
        'genres': list(profile['genres'].keys())[:5]
    }
    
    prompt = f"""
    [DEEP TASTE DNA]
    Loved: {', '.join(context['loved'][:10])}
    Liked: {', '.join(context['liked'][:10])}
    Top Genres: {', '.join(context['genres'])}
    Disliked Genres: {', '.join(profile.get('disliked_genres', []))}
    
    [EXCLUDE THESE TITLES - USER HAS ALREADY WATCHED]
    {', '.join(all_tracked_titles)}
    
    [TASK]
    Suggest exactly 3 NEW 'Deep Intelligence' matches. These should be 'Thematic Siblings'—media that shares the same tone, writing style, or philosophical themes as the loved list.
    Avoid anything in the Disliked Genres.
    Focus on finding 'Hidden Gems' (high quality but perhaps less mainstream).
    
    Output ONLY a JSON array of titles. No explanation.
    Example: ["New Title 1", "New Title 2", "New Title 3"]
    """
    
    titles = []
    try:
        response = analyst.chat_with_library(prompt, [], refresh=refresh)
        match = re.search(r'\[\s*".*"\s*\]', response, re.DOTALL)
        if match:
            titles = json.loads(match.group())
        else:
            titles = re.findall(r'"([^"]*)"', response)[:3]
    except: pass
    
    if not titles:
        titles = ["Devs", "Better Off Ted", "Lapsis"]
        
    results = []
    for title in titles[:3]:
        data = client.search_by_title(title)
        if data:
            score_data = calculate_match_score(data, profile)
            results.append({
                'id': None,
                'title': data.get('Title'),
                'year': data.get('Year'),
                'genre': data.get('Genre'),
                'genres': data.get('Genre'),
                'media_type': data.get('Type'),
                'poster': data.get('Poster'),
                'summary': data.get('Plot'),
                'match': score_data,
                'vibe': score_data.get('vibe'),
                'on_netflix': False,
                'youtube_url': f"https://www.youtube.com/results?search_query={data.get('Title').replace(' ', '+')}+{data.get('Type', '')}+funny+clips".replace('++', '+')
            })
    
    return jsonify(results), 200

@ai_bp.route('/api/discover', methods=['GET'])
def discover_media():
    query = request.args.get('q')
    if not query:
        return jsonify({'error': 'No search query provided'}), 400
        
    client = OMDBClient()
    data = client.search_by_title(query)
    
    if not data:
        return jsonify({'error': 'No results found'}), 404
        
    profile = get_user_taste_profile()
    score_data = calculate_match_score(data, profile)
    
    local_media = Media.query.filter_by(title=data.get('Title')).first()
    
    return jsonify({
        'id': local_media.id if local_media else None,
        'title': data.get('Title'),
        'media_type': data.get('Type'),
        'year': data.get('Year'),
        'genre': data.get('Genre'),
        'genres': data.get('Genre'),
        'runtime': data.get('Runtime'),
        'total_seasons': data.get('totalSeasons'),
        'plot': data.get('Plot'),
        'poster': data.get('Poster'),
        'match': score_data,
        'local_rating': local_media.user_rating if local_media else 0,
        'youtube_url': f"https://www.youtube.com/results?search_query={data.get('Title').replace(' ', '+')}+{data.get('Type', '')}+funny+clips".replace('++', '+')
    })

@ai_bp.route('/api/suggestions', methods=['GET'])
def get_suggestions():
    people = request.args.getlist('person')
    genres = request.args.getlist('genre')
    themes = request.args.getlist('theme')
    moods = request.args.getlist('mood')
    aesthetics = request.args.getlist('aesthetic')
    refresh = request.args.get('refresh', 'false').lower() == 'true'
    
    try:
        suggestions = get_proactive_suggestions(
            db, 
            limit=20, 
            target_people=people, 
            target_genres=genres, 
            target_themes=themes,
            target_moods=moods,
            target_aesthetics=aesthetics,
            refresh=refresh
        )
        return jsonify(suggestions), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

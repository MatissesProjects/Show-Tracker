
from flask import Blueprint, jsonify, request
from database import db
from models import Media, WatchHistory
from utils.omdb import OMDBClient
from utils.enricher import apply_metadata, enrich_media_data
from utils.parser import parse_netflix_history
from utils.backup import backup_database
from utils.title_cleaner import clean_netflix_title
from utils.recommender import get_user_taste_profile, calculate_match_score
from utils.ai_analyst import AIAnalyst
from sqlalchemy import or_

media_bp = Blueprint('media', __name__)

@media_bp.route('/api/media', methods=['GET'])
def get_media():
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)

    # Filter for items NOT in watchlist
    query = Media.query.filter(
        or_(Media.in_watchlist == False, Media.in_watchlist == None)
    )
    
    media_list = query.order_by(
        (Media.user_rating == 0).desc(), 
        Media.id.desc()
    ).paginate(page=page, per_page=per_page, error_out=False)
    
    return jsonify({
        'items': [m.to_dict() for m in media_list.items],
        'total': media_list.total,
        'page': page,
        'pages': media_list.pages
    })

@media_bp.route('/api/media/<int:media_id>/rate', methods=['POST'])
def rate_media(media_id):
    rating = request.json.get('rating')
    media = db.session.get(Media, media_id)
    if not media: return jsonify({'error': 'Media not found'}), 404
    
    media.user_rating = rating
    # Rating an item implies it has been watched, so remove from watchlist
    media.in_watchlist = False
    
    # Add to history if not already there
    if not WatchHistory.query.filter_by(media_id=media.id).first():
        history = WatchHistory(media_id=media.id, platform='Manual')
        db.session.add(history)
        
    db.session.commit()
    return jsonify({'message': 'Rating updated'}), 200

@media_bp.route('/api/media/<int:media_id>/watchlist', methods=['POST'])
def toggle_watchlist(media_id):
    media = db.session.get(Media, media_id)
    if not media: return jsonify({'error': 'Media not found'}), 404
    media.in_watchlist = not media.in_watchlist
    db.session.commit()
    return jsonify({'message': 'Watchlist updated', 'in_watchlist': media.in_watchlist}), 200

@media_bp.route('/api/watchlist', methods=['GET'])
def get_watchlist():
    items = Media.query.filter_by(in_watchlist=True).all()
    return jsonify([m.to_dict() for m in items]), 200

@media_bp.route('/api/media/rate-external', methods=['POST'])
def rate_external_media():
    data = request.json
    title = data.get('title')
    rating = data.get('rating')
    
    if not title or rating not in [2, 1, -1, 0]:
        return jsonify({'error': 'Invalid data'}), 400
        
    media = Media.query.filter_by(title=title).first()
    if not media:
        media = Media(title=title, media_type='unknown')
        db.session.add(media)
        db.session.flush()
        
        client = OMDBClient()
        omdb_data = client.search_by_title(title)
        if omdb_data:
            apply_metadata(media, omdb_data, db)
    
    media.user_rating = rating
    
    if rating == 0:
        media.in_watchlist = True
    else:
        media.in_watchlist = False
        if not WatchHistory.query.filter_by(media_id=media.id).first():
            history = WatchHistory(media_id=media.id, platform='Discovered')
            db.session.add(history)
        
    db.session.commit()
    return jsonify({'message': 'Media processed successfully'}), 200

@media_bp.route('/api/media/<int:media_id>/details', methods=['GET'])
def get_media_details(media_id):
    m = db.session.get(Media, media_id)
    if not m: return jsonify({'error': 'Media not found'}), 404
    profile = get_user_taste_profile()
    
    actors = ", ".join([mp.person.name for mp in m.person_memberships if mp.role == 'Actor'])
    director = ", ".join([mp.person.name for mp in m.person_memberships if mp.role == 'Director'])
    
    media_data = {
        'Actors': actors,
        'Director': director,
        'Genre': m.genres,
        'imdbRating': m.rating
    }
    
    score_data = calculate_match_score(media_data, profile)
    
    # Generate/Retrieve AI Insight & Thematic DNA
    ai_insight = m.ai_insight
    thematic_dna = m.thematic_metadata
    
    if not ai_insight or not thematic_dna:
        analyst = AIAnalyst()
        if analyst.check_availability():
            if not ai_insight:
                ai_insight = analyst.generate_insight(m.title, media_data, profile)
                m.ai_insight = ai_insight
            
            if not thematic_dna:
                dna_obj = analyst.extract_thematic_dna(m.title, media_data)
                if dna_obj:
                    m.thematic_metadata = json.dumps(dna_obj)
                    thematic_dna = m.thematic_metadata
            
            db.session.commit()

    result = m.to_dict()
    result.update({
        'year': m.release_date[:4] if m.release_date else '????',
        'poster': m.poster_url,
        'summary': m.overview or "No description available.",
        'match': score_data,
        'ai_insight': ai_insight,
        'thematic_dna': json.loads(thematic_dna) if thematic_dna else None,
        'youtube_url': f"https://www.youtube.com/results?search_query={m.title.replace(' ', '+')}+funny+moments+clips",
        'on_netflix': False 
    })
    
    return jsonify(result), 200

@media_bp.route('/api/media/<int:media_id>/refresh', methods=['POST'])
def refresh_media_data(media_id):
    media = db.session.get(Media, media_id)
    if not media: return jsonify({'error': 'Media not found'}), 404
    client = OMDBClient()
    
    data = client.search_by_title(media.title)
    if not data:
        base_title = clean_netflix_title(media.title)
        data = client.search_by_title(base_title)
        
    if data:
        apply_metadata(media, data, db)
        db.session.commit()
        return jsonify({'message': 'Metadata refreshed', 'poster_url': media.poster_url}), 200
    
    return jsonify({'error': 'Could not find updated data for this title'}), 404

@media_bp.route('/api/upload-netflix', methods=['POST'])
def upload_netflix():
    backup_database()
    
    if 'file' not in request.files:
        return jsonify({'error': 'No file part'}), 400
        
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No selected file'}), 400
        
    try:
        count = parse_netflix_history(file.read(), db)
        return jsonify({'message': f'Successfully imported {count} new entries'}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@media_bp.route('/api/enrich', methods=['POST'])
def enrich_data():
    backup_database()
    try:
        enriched_count, dna_count = enrich_media_data(db)
        return jsonify({
            'message': f'Successfully enriched {enriched_count} unique titles and extracted {dna_count} DNA signatures'
        }), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

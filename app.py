from flask import Flask, jsonify
from flask_cors import CORS
from database import db
import os


def create_app():
    app = Flask(__name__)
    
    # Configure SQLite database
    basedir = os.path.abspath(os.path.dirname(__file__))
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(basedir, 'show_tracker.db')
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    
    CORS(app, resources={r"/api/*": {"origins": "*"}})
    db.init_app(app)
    
    with app.app_context():
        # Backup before any potential schema changes
        from utils.backup import backup_database
        backup_database()
        
        # Import models here to ensure they are registered before create_all
        import models
        db.create_all()
    
    @app.errorhandler(Exception)
    def handle_exception(e):
        app.logger.error(f"Server Error: {str(e)}")
        import traceback
        app.logger.error(traceback.format_exc())
        return jsonify({"error": "Internal Server Error", "details": str(e)}), 500

    @app.route('/api/backup', methods=['POST'])
    def manual_backup():
        from utils.backup import backup_database
        path = backup_database()
        if path:
            return jsonify({'message': f'Backup created at {path}'}), 200
        return jsonify({'error': 'Backup failed'}), 500

    @app.route('/api/health')
    def health_check():
        return {'status': 'healthy', 'message': 'Show Tracker API is running'}

    @app.route('/api/upload-netflix', methods=['POST'])
    def upload_netflix():
        from flask import request
        from utils.parser import parse_netflix_history
        from utils.backup import backup_database
        
        backup_database() # Safety first
        
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

    @app.route('/api/enrich', methods=['POST'])
    def enrich_data():
        from utils.enricher import enrich_media_data
        from utils.backup import backup_database
        backup_database()
        try:
            count = enrich_media_data(db)
            return jsonify({'message': f'Successfully enriched {count} unique titles'}), 200
        except Exception as e:
            return jsonify({'error': str(e)}), 500

    @app.route('/api/media', methods=['GET'])
    def get_media():
        from models import Media
        from sqlalchemy import func, or_
        from flask import request
        
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 20, type=int)

        # Optimization: Use a simpler query and let paginate handle the count
        # Filter for items NOT in watchlist
        query = Media.query.filter(
            or_(Media.in_watchlist == False, Media.in_watchlist == None)
        )
        
        # Deduplicate by title if needed, or just order by rating and ID
        # Since we deduplicate in the parser/enricher, we can usually just query Media
        # But to be safe against OMDb title normalization duplicates:
        media_list = query.order_by(
            (Media.user_rating == 0).desc(), 
            Media.id.desc()
        ).paginate(page=page, per_page=per_page, error_out=False)
        
        return jsonify({
            'items': [{
                'id': m.id,
                'title': m.title,
                'media_type': m.media_type,
                'release_date': m.release_date,
                'rating': m.rating,
                'genres': m.genres,
                'runtime': m.runtime,
                'poster_url': m.poster_url,
                'user_rating': m.user_rating,
                'in_watchlist': m.in_watchlist or False
            } for m in media_list.items],
            'total': media_list.total,
            'page': page,
            'pages': media_list.pages
        })

    @app.route('/api/stats/people', methods=['GET'])
    def get_people_stats():
        from utils.analyzer import get_top_people
        try:
            stats = get_top_people()
            return jsonify(stats), 200
        except Exception as e:
            return jsonify({'error': str(e)}), 500

    @app.route('/api/media/<int:media_id>/rate', methods=['POST'])
    def rate_media(media_id):
        from flask import request
        from models import Media, WatchHistory
        rating = request.json.get('rating')
        media = Media.query.get(media_id)
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

    @app.route('/api/media/<int:media_id>/details', methods=['GET'])
    def get_media_details(media_id):
        from models import Media
        from utils.recommender import get_user_taste_profile, calculate_match_score
        
        m = Media.query.get_or_404(media_id)
        profile = get_user_taste_profile()
        
        actors = ", ".join([mp.person.name for mp in m.person_memberships if mp.role == 'Actor'])
        director = ", ".join([mp.person.name for mp in m.person_memberships if mp.role == 'Director'])
        writer = ", ".join([mp.person.name for mp in m.person_memberships if mp.role == 'Writer'])
        
        media_data = {
            'Actors': actors,
            'Director': director,
            'Writer': writer,
            'Genre': m.genres,
            'imdbRating': m.rating
        }
        
        score_data = calculate_match_score(media_data, profile)
        
        return jsonify({
            'id': m.id,
            'title': m.title,
            'year': m.release_date[:4] if m.release_date else '????',
            'genre': m.genres,
            'poster': m.poster_url,
            'summary': m.overview or "No description available.",
            'match': score_data,
            'youtube_url': f"https://www.youtube.com/results?search_query={m.title.replace(' ', '+')}+funny+moments+clips",
            'on_netflix': False 
        })

    @app.route('/api/media/<int:media_id>/watchlist', methods=['POST'])
    def toggle_watchlist(media_id):
        from models import Media
        media = Media.query.get(media_id)
        if not media: return jsonify({'error': 'Media not found'}), 404
        media.in_watchlist = not media.in_watchlist
        db.session.commit()
        return jsonify({'message': 'Watchlist updated', 'in_watchlist': media.in_watchlist}), 200

    @app.route('/api/watchlist', methods=['GET'])
    def get_watchlist():
        from models import Media
        items = Media.query.filter_by(in_watchlist=True).all()
        return jsonify([{
            'id': m.id,
            'title': m.title,
            'media_type': m.media_type,
            'genres': m.genres,
            'rating': m.rating,
            'poster_url': m.poster_url
        } for m in items]), 200

    @app.route('/api/media/rate-external', methods=['POST'])
    def rate_external_media():
        from flask import request
        from models import Media, WatchHistory
        from utils.omdb import OMDBClient
        from utils.enricher import apply_metadata
        
        data = request.json
        title = data.get('title')
        rating = data.get('rating') # can be 1, -1, or 0
        
        if not title or rating not in [1, -1, 0]:
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
            # Neutral rating from discovery means "Add to Watchlist"
            media.in_watchlist = True
        else:
            # Thumbs up/down means "I watched this", so ensure it's not in watchlist
            media.in_watchlist = False
            # Add to watch history
            if not WatchHistory.query.filter_by(media_id=media.id).first():
                history = WatchHistory(media_id=media.id, platform='Discovered')
                db.session.add(history)
            
        db.session.commit()
        return jsonify({'message': 'Media processed successfully'}), 200

    @app.route('/api/stats/genres', methods=['GET'])
    def get_genre_stats_api():
        from utils.analyzer import get_genre_stats
        try:
            stats = get_genre_stats()
            return jsonify(stats), 200
        except Exception as e:
            return jsonify({'error': str(e)}), 500

    @app.route('/api/discover', methods=['GET'])
    def discover_media():
        from flask import request
        from utils.omdb import OMDBClient
        from utils.recommender import get_user_taste_profile, calculate_match_score
        from models import Media
        
        query = request.args.get('q')
        if not query:
            return jsonify({'error': 'No search query provided'}), 400
            
        client = OMDBClient()
        data = client.search_by_title(query)
        
        if not data:
            return jsonify({'error': 'No results found'}), 404
            
        profile = get_user_taste_profile()
        score_data = calculate_match_score(data, profile)
        
        # Check if we already have this in our DB
        local_media = Media.query.filter_by(title=data.get('Title')).first()
        
        return jsonify({
            'id': local_media.id if local_media else None,
            'title': data.get('Title'),
            'year': data.get('Year'),
            'genre': data.get('Genre'),
            'plot': data.get('Plot'),
            'poster': data.get('Poster'),
            'match': score_data,
            'local_rating': local_media.user_rating if local_media else 0
        })

    @app.route('/api/suggestions', methods=['GET'])
    def get_suggestions():
        from flask import request
        from utils.recommender import get_proactive_suggestions
        
        # Support multiple parameters like ?person=A&person=B
        people = request.args.getlist('person')
        genres = request.args.getlist('genre')
        
        try:
            suggestions = get_proactive_suggestions(db, limit=20, target_people=people, target_genres=genres)
            return jsonify(suggestions), 200
        except Exception as e:
            return jsonify({'error': str(e)}), 500
        
    return app

if __name__ == '__main__':
    app = create_app()
    app.run(debug=True, port=5000)

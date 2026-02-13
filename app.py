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
        # Import models here to ensure they are registered before create_all
        import models
        db.create_all()
    
    @app.errorhandler(Exception)
    def handle_exception(e):
        app.logger.error(f"Server Error: {str(e)}")
        import traceback
        app.logger.error(traceback.format_exc())
        return jsonify({"error": "Internal Server Error", "details": str(e)}), 500

    @app.route('/api/health')
    def health_check():
        return {'status': 'healthy', 'message': 'Show Tracker API is running'}

    @app.route('/api/upload-netflix', methods=['POST'])
    def upload_netflix():
        from flask import request
        from utils.parser import parse_netflix_history
        
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
        try:
            count = enrich_media_data(db)
            return jsonify({'message': f'Successfully enriched {count} unique titles'}), 200
        except Exception as e:
            return jsonify({'error': str(e)}), 500

    @app.route('/api/media', methods=['GET'])
    def get_media():
        from models import Media
        from sqlalchemy import func
        # Group by title to show unique shows/movies
        # We use a subquery to find the latest ID for each unique title
        subquery = db.session.query(
            func.max(Media.id).label('max_id')
        ).group_by(Media.title).subquery()
        
        # We also limit to 50 for the UI but you can adjust this
        media_list = Media.query.filter(Media.id.in_(subquery)).order_by(Media.id.desc()).limit(100).all()
        
        return jsonify([{
            'id': m.id,
            'title': m.title,
            'media_type': m.media_type,
            'release_date': m.release_date,
            'rating': m.rating,
            'genres': m.genres,
            'runtime': m.runtime,
            'user_rating': m.user_rating
        } for m in media_list])

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
        from models import Media
        rating = request.json.get('rating') # 1, -1, or 0
        if rating not in [1, -1, 0]:
            return jsonify({'error': 'Invalid rating'}), 400
            
        media = Media.query.get(media_id)
        if not media:
            return jsonify({'error': 'Media not found'}), 404
            
        media.user_rating = rating
        db.session.commit()
        return jsonify({'message': 'Rating updated successfully'}), 200

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
        
        query = request.args.get('q')
        if not query:
            return jsonify({'error': 'No search query provided'}), 400
            
        client = OMDBClient()
        data = client.search_by_title(query)
        
        if not data:
            return jsonify({'error': 'No results found'}), 404
            
        profile = get_user_taste_profile()
        score_data = calculate_match_score(data, profile)
        
        return jsonify({
            'title': data.get('Title'),
            'year': data.get('Year'),
            'genre': data.get('Genre'),
            'plot': data.get('Plot'),
            'poster': data.get('Poster'),
            'match': score_data
        })
        
    return app

if __name__ == '__main__':
    app = create_app()
    app.run(debug=True, port=5000)

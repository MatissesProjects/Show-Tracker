
from flask import Flask, jsonify
from flask_cors import CORS
from database import db
import os

# Import blueprints
from routes.media import media_bp
from routes.ai import ai_bp
from routes.stats import stats_bp
from routes.core import core_bp

def create_app():
    app = Flask(__name__)
    
    # Configure SQLite database
    basedir = os.path.abspath(os.path.dirname(__file__))
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(basedir, 'show_tracker.db')
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    
    CORS(app, resources={r"/api/*": {"origins": "*"}})
    db.init_app(app)
    
    # Register Blueprints
    app.register_blueprint(media_bp)
    app.register_blueprint(ai_bp)
    app.register_blueprint(stats_bp)
    app.register_blueprint(core_bp)
    
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
        
    return app

if __name__ == '__main__':
    app = create_app()
    app.run(debug=True, port=5000)

from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS
import os

db = SQLAlchemy()

def create_app():
    app = Flask(__name__)
    
    # Configure SQLite database
    basedir = os.path.abspath(os.path.dirname(__file__))
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(basedir, 'show_tracker.db')
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    
    CORS(app)
    db.init_app(app)
    
    with app.app_context():
        import models
        db.create_all()
    
    @app.route('/api/health')
    def health_check():
        return {'status': 'healthy', 'message': 'Show Tracker API is running'}
        
    return app

if __name__ == '__main__':
    app = create_app()
    app.run(debug=True, port=5000)

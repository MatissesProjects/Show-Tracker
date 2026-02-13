import pytest
from models import Media, Person, MediaPerson, WatchHistory
from app import db

def test_health_check(client):
    """Test the health check endpoint."""
    response = client.get('/api/health')
    assert response.status_code == 200
    assert response.json['status'] == 'healthy'

def test_media_model(app):
    """Test creating a Media entry with all fields."""
    with app.app_context():
        media = Media(
            title="Inception", 
            media_type="movie", 
            tmdb_id=27205, 
            release_date="2010-07-15",
            overview="A thief who steals corporate secrets..."
        )
        db.session.add(media)
        db.session.commit()
        
        saved = Media.query.filter_by(tmdb_id=27205).first()
        assert saved.title == "Inception"
        assert saved.media_type == "movie"

def test_media_person_roles(app):
    """Test that a person can have multiple roles (Actor and Director)."""
    with app.app_context():
        movie = Media(title="Interstellar", media_type="movie")
        nolan = Person(name="Christopher Nolan")
        
        # Add Nolan as Director
        role1 = MediaPerson(media=movie, person=nolan, role="Director")
        # Add Nolan as Writer (hypothetically)
        role2 = MediaPerson(media=movie, person=nolan, role="Writer")
        
        db.session.add_all([movie, nolan, role1, role2])
        db.session.commit()
        
        saved_movie = Media.query.filter_by(title="Interstellar").first()
        assert len(saved_movie.person_memberships) == 2
        roles = [m.role for m in saved_movie.person_memberships]
        assert "Director" in roles
        assert "Writer" in roles

def test_watch_history_link(app):
    """Test that watch history links correctly to media."""
    with app.app_context():
        movie = Media(title="The Matrix", media_type="movie")
        db.session.add(movie)
        db.session.commit()
        
        entry = WatchHistory(media_id=movie.id, platform="Netflix")
        db.session.add(entry)
        db.session.commit()
        
        saved_entry = WatchHistory.query.first()
        assert saved_entry.media.title == "The Matrix"
        assert saved_entry.platform == "Netflix"

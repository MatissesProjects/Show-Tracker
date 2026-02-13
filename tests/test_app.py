import pytest
from models import Media, Person, WatchHistory
from app import db

def test_health_check(client):
    """Test the health check endpoint."""
    response = client.get('/api/health')
    assert response.status_code == 200
    assert response.json['status'] == 'healthy'

def test_media_model(app):
    """Test creating a Media entry."""
    with app.app_context():
        media = Media(title="Inception", media_type="movie")
        db.session.add(media)
        db.session.commit()
        
        saved_media = Media.query.filter_by(title="Inception").first()
        assert saved_media is not None
        assert saved_media.title == "Inception"

def test_media_person_relationship(app):
    """Test the Many-to-Many relationship between Media and Person."""
    with app.app_context():
        movie = Media(title="Interstellar", media_type="movie")
        actor = Person(name="Matthew McConaughey")
        
        movie.people.append(actor)
        db.session.add(movie)
        db.session.add(actor)
        db.session.commit()
        
        saved_movie = Media.query.filter_by(title="Interstellar").first()
        assert len(saved_movie.people) == 1
        assert saved_movie.people[0].name == "Matthew McConaughey"
        
        saved_person = Person.query.filter_by(name="Matthew McConaughey").first()
        assert len(saved_person.media_works.all()) == 1

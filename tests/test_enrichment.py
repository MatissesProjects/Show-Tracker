import pytest
from unittest.mock import patch
from models import Media, Person, MediaPerson
from database import db

@patch('utils.omdb.requests.get')
def test_refresh_media(mock_get, client, app):
    """Test refreshing media metadata from OMDb."""
    # Mock OMDb response
    mock_get.return_value.status_code = 200
    mock_get.return_value.json.return_value = {
        'Response': 'True',
        'Title': 'Inception',
        'Type': 'movie',
        'Released': '16 Jul 2010',
        'Plot': 'A thief who steals corporate secrets...',
        'Genre': 'Action, Sci-Fi',
        'imdbRating': '8.8',
        'Runtime': '148 min',
        'Poster': 'http://test.com/poster.jpg'
    }

    with app.app_context():
        m = Media(title="Inception", media_type="unknown")
        db.session.add(m)
        db.session.commit()
        media_id = m.id

    response = client.post(f'/api/media/{media_id}/refresh')
    assert response.status_code == 200
    assert response.json['poster_url'] == 'http://test.com/poster.jpg'

    with app.app_context():
        saved = db.session.get(Media, media_id)
        assert saved.rating == '8.8'
        assert saved.genres == 'Action, Sci-Fi'
        assert saved.release_date == '16 Jul 2010'

def test_get_media_details(client, app):
    """Test the detailed media view endpoint."""
    with app.app_context():
        m = Media(
            title="Succession", 
            media_type="series", 
            release_date="2018-06-03",
            overview="The Roy family is known for controlling the biggest media and entertainment company in the world.",
            genres="Drama",
            rating="8.9",
            runtime="60 min",
            total_seasons="4"
        )
        db.session.add(m)
        db.session.commit()
        media_id = m.id

    response = client.get(f'/api/media/{media_id}/details')
    assert response.status_code == 200
    assert response.json['title'] == "Succession"
    assert response.json['total_seasons'] == "4"
    assert response.json['runtime'] == "60 min"
    assert 'match' in response.json

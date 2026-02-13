import pytest
from models import Media
from database import db

def test_get_watchlist_empty(client):
    """Test fetching an empty watchlist."""
    response = client.get('/api/watchlist')
    assert response.status_code == 200
    assert response.json == []

def test_toggle_watchlist(client, app):
    """Test adding and removing from watchlist."""
    with app.app_context():
        m = Media(title="Test Show", media_type="series")
        db.session.add(m)
        db.session.commit()
        media_id = m.id

    # Add to watchlist
    response = client.post(f'/api/media/{media_id}/watchlist')
    assert response.status_code == 200
    assert response.json['in_watchlist'] == True

    # Check watchlist
    response = client.get('/api/watchlist')
    assert len(response.json) == 1
    assert response.json[0]['title'] == "Test Show"

    # Remove from watchlist
    response = client.post(f'/api/media/{media_id}/watchlist')
    assert response.status_code == 200
    assert response.json['in_watchlist'] == False

    # Check watchlist again
    response = client.get('/api/watchlist')
    assert len(response.json) == 0

def test_rate_external_to_watchlist(client, app):
    """Test that rating 0 adds external media to watchlist."""
    data = {'title': 'External Show', 'rating': 0}
    response = client.post('/api/media/rate-external', json=data)
    assert response.status_code == 200
    
    with app.app_context():
        m = Media.query.filter_by(title='External Show').first()
        assert m.in_watchlist == True
        assert m.user_rating == 0

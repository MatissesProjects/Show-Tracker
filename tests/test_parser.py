import pytest
import io
from models import Media, WatchHistory
from database import db

def test_netflix_upload(client, app):
    """Test uploading a mock Netflix CSV."""
    csv_content = "Title,Date\nStranger Things: Season 1: Chapter One,2023-01-01\nInception,2023-01-02\n"
    
    data = {
        'file': (io.BytesIO(csv_content.encode('utf-8')), 'ViewingActivity.csv')
    }
    
    response = client.post('/api/upload-netflix', data=data, content_type='multipart/form-data')
    
    assert response.status_code == 200
    assert "Successfully imported 2" in response.json['message']
    
    with app.app_context():
        # Check Media creation
        st = Media.query.filter_by(title="Stranger Things").first()
        assert st is not None
        
        # Check WatchHistory creation
        history = WatchHistory.query.all()
        assert len(history) == 2

def test_netflix_upload_duplicate(client, app):
    """Test that duplicate entries are not created."""
    csv_content = "Title,Date\nInception,2023-01-02\n"
    data = {'file': (io.BytesIO(csv_content.encode('utf-8')), 'ViewingActivity.csv')}
    
    # Upload once
    client.post('/api/upload-netflix', data=data, content_type='multipart/form-data')
    
    # Upload again
    data['file'] = (io.BytesIO(csv_content.encode('utf-8')), 'ViewingActivity.csv')
    response = client.post('/api/upload-netflix', data=data, content_type='multipart/form-data')
    
    assert "Successfully imported 0" in response.json['message']

def test_netflix_encoding_special_chars(client, app):
    """Test uploading Netflix CSV with special characters and different encodings."""
    # Pokémon in UTF-8 with BOM
    csv_content = "Title,Date\nPokémon,2023-01-01\n"
    data = {
        'file': (io.BytesIO(csv_content.encode('utf-8-sig')), 'ViewingActivity.csv')
    }
    
    response = client.post('/api/upload-netflix', data=data, content_type='multipart/form-data')
    assert response.status_code == 200
    
    with app.app_context():
        p = Media.query.filter_by(title="Pokémon").first()
        assert p is not None
        assert p.title == "Pokémon"

    # Amélie in Latin-1
    csv_content_latin1 = "Title,Date\nAmélie,2023-01-02\n"
    data_latin1 = {
        'file': (io.BytesIO(csv_content_latin1.encode('latin-1')), 'ViewingActivity.csv')
    }
    
    response = client.post('/api/upload-netflix', data=data_latin1, content_type='multipart/form-data')
    assert response.status_code == 200
    
    with app.app_context():
        a = Media.query.filter_by(title="Amélie").first()
        assert a is not None
        assert a.title == "Amélie"

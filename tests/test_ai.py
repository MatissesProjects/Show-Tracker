import pytest
from unittest.mock import patch, MagicMock
from models import Media
from database import db
import os

@patch('utils.ai_analyst.requests.get')
def test_ai_status_available(mock_get, client):
    """Test AI status when Ollama is available."""
    os.environ['OLLAMA_URL'] = 'http://localhost:11434'
    mock_get.return_value.status_code = 200
    
    response = client.get('/api/ai/status')
    assert response.status_code == 200
    assert response.json['available'] == True

def test_ai_status_unavailable(client):
    """Test AI status when OLLAMA_URL is not set."""
    if 'OLLAMA_URL' in os.environ:
        del os.environ['OLLAMA_URL']
    
    response = client.get('/api/ai/status')
    assert response.status_code == 200
    assert response.json['available'] == False

@patch('utils.ai_analyst.requests.post')
@patch('utils.omdb.requests.get')
def test_deep_discovery(mock_omdb, mock_ollama, client, app):
    """Test the deep discovery synthesis endpoint."""
    # Mock Ollama response (JSON titles)
    mock_ollama.return_value.status_code = 200
    mock_ollama.return_value.json.return_value = {
        'response': '["Test Gem 1", "Test Gem 2"]'
    }

    # Mock OMDb response
    mock_omdb.return_value.status_code = 200
    mock_omdb.return_value.json.return_value = {
        'Response': 'True',
        'Title': 'Test Gem 1',
        'Year': '2024',
        'Genre': 'Sci-Fi',
        'Plot': 'A cool show.',
        'Poster': 'N/A'
    }

    response = client.get('/api/ai/deep-discovery')
    assert response.status_code == 200
    assert len(response.json) > 0
    assert response.json[0]['title'] == 'Test Gem 1'

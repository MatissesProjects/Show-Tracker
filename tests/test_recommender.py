import pytest
from utils.recommender import calculate_match_score, get_user_taste_profile
from models import Media, Person, MediaPerson
from database import db

def test_match_score_calculation(app):
    """Test that the match score reflects user preferences."""
    with app.app_context():
        # Setup user profile
        m1 = Media(title="Show A", user_rating=2, genres="Sci-Fi")
        m2 = Media(title="Show B", user_rating=-1, genres="Romance")
        p1 = Person(name="Cool Actor")
        db.session.add_all([m1, m2, p1])
        db.session.commit()
        
        # Link actor to loved show
        role = MediaPerson(media=m1, person=p1, role="Actor")
        db.session.add(role)
        db.session.commit()
        
        profile = get_user_taste_profile()
        
        # Test 1: High match (matching loved genre and actor)
        media_data = {
            'Actors': 'Cool Actor',
            'Genre': 'Sci-Fi',
            'imdbRating': '9.0'
        }
        score_data = calculate_match_score(media_data, profile)
        assert score_data['total_score'] > 50
        assert any("Starring/Created by Cool Actor" in d for d in score_data['breakdown'])

        # Test 2: Low match (disliked genre)
        media_data_low = {
            'Actors': 'Unknown Person',
            'Genre': 'Romance',
            'imdbRating': '5.0'
        }
        score_data_low = calculate_match_score(media_data_low, profile)
        # Sci-Fi match should be higher than Romance
        assert score_data['total_score'] > score_data_low['total_score']

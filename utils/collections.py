from models import Media, Person, MediaPerson, WatchHistory
from database import db
from utils.recommender import get_user_taste_profile
import json
import random

def get_smart_collections():
    """Generates dynamic groupings of media based on deep library DNA."""
    profile = get_user_taste_profile()
    collections = []

    # 1. The "Top Talent" Collection
    # Find the top loved person and get all their works in the library
    top_people = sorted(profile['people'].items(), key=lambda x: x[1], reverse=True)
    if top_people:
        for person_name, score in top_people[:2]:
            if score > 2.0: # Significant affinity
                talent_media = Media.query.join(MediaPerson).join(Person).filter(
                    Person.name == person_name
                ).all()
                
                if len(talent_media) >= 3:
                    items = [m.to_dict() for m in talent_media]
                    random.shuffle(items)
                    collections.append({
                        'id': f'talent_{person_name.lower().replace(" ", "_")}',
                        'title': f'The {person_name} Collection',
                        'subtitle': f'Based on your affinity for {person_name}',
                        'type': 'talent',
                        'seed': person_name,
                        'items': items
                    })

    # 2. "Masterpiece" Genre Collections
    # Top genre with items rated > 8.0
    top_genres = sorted(profile['genres'].items(), key=lambda x: x[1], reverse=True)
    if top_genres:
        for genre_name, score in top_genres[:2]:
            masterpieces = Media.query.filter(
                Media.genres.like(f'%{genre_name}%'),
                Media.rating >= '8.0'
            ).all()
            
            if len(masterpieces) >= 3:
                items = [m.to_dict() for m in masterpieces]
                random.shuffle(items)
                collections.append({
                    'id': f'masterpiece_{genre_name.lower()}',
                    'title': f'{genre_name} Masterpieces',
                    'subtitle': f'Top-tier {genre_name.lower()} from your library',
                    'type': 'genre',
                    'seed': genre_name,
                    'items': items
                })

    # 3. "Vibe" Collections
    # Group by Mood/Aesthetic from thematic_metadata
    moods = sorted(profile['moods'].items(), key=lambda x: x[1], reverse=True)
    if moods:
        for mood_name, score in moods[:2]:
            mood_media = Media.query.filter(
                Media.thematic_metadata.like(f'%"{mood_name}"%')
            ).all()
            
            if len(mood_media) >= 3:
                items = [m.to_dict() for m in mood_media]
                random.shuffle(items)
                collections.append({
                    'id': f'vibe_{mood_name.lower()}',
                    'title': f'The {mood_name} Vibe',
                    'subtitle': f'Media that matches your {mood_name.lower()} mood',
                    'type': 'vibe',
                    'seed': mood_name,
                    'items': items
                })

    return collections

from database import db
from models import Media, Person, MediaPerson
from utils.omdb import OMDBClient
from utils.title_cleaner import clean_netflix_title

def enrich_media_data(db_instance):
    """
    Finds unique 'unknown' media, cleans their titles, 
    and fetches data from OMDb.
    """
    client = OMDBClient()
    
    # Get all unique unknown media
    unknown_media = db_instance.session.query(Media).filter_by(media_type='unknown').all()
    
    # Track unique base titles to avoid redundant API calls
    processed_titles = {}
    
    enriched_count = 0
    for media in unknown_media:
        base_title = clean_netflix_title(media.title)
        
        if base_title in processed_titles:
            # Reuse data if we've already fetched it for this series
            apply_metadata(media, processed_titles[base_title], db_instance)
            continue
            
        data = client.search_by_title(base_title)
        if data:
            processed_titles[base_title] = data
            apply_metadata(media, data, db_instance)
            enriched_count += 1
            
    db_instance.session.commit()
    return enriched_count

def apply_metadata(media, data, db_instance):
    """Applies OMDb data to a media object and its relationships."""
    media.title = data.get('Title', media.title)
    media.media_type = data.get('Type')
    media.release_date = data.get('Released')
    media.overview = data.get('Plot')
    
    # Process Actors
    actors = data.get('Actors', '').split(', ')
    for actor_name in actors:
        if actor_name and actor_name != 'N/A':
            person = get_or_create_person(actor_name, db_instance)
            add_role(media, person, 'Actor', db_instance)
            
    # Process Director
    directors = data.get('Director', '').split(', ')
    for director_name in directors:
        if director_name and director_name != 'N/A':
            person = get_or_create_person(director_name, db_instance)
            add_role(media, person, 'Director', db_instance)

    # Process Writer/Creator
    writers = data.get('Writer', '').split(', ')
    for writer_name in writers:
        if writer_name and writer_name != 'N/A':
            # Clean " (written by)" etc from writer names
            clean_name = writer_name.split(' (')[0]
            person = get_or_create_person(clean_name, db_instance)
            add_role(media, person, 'Creator', db_instance)

def get_or_create_person(name, db_instance):
    person = db_instance.session.query(Person).filter_by(name=name).first()
    if not person:
        person = Person(name=name)
        db_instance.session.add(person)
        db_instance.session.flush()
    return person

def add_role(media, person, role, db_instance):
    existing = db_instance.session.query(MediaPerson).filter_by(
        media_id=media.id,
        person_id=person.id,
        role=role
    ).first()
    
    if not existing:
        new_role = MediaPerson(media=media, person=person, role=role)
        db_instance.session.add(new_role)

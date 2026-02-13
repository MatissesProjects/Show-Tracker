from database import db
from models import Media, Person, MediaPerson
from utils.omdb import OMDBClient
from utils.title_cleaner import clean_netflix_title

def enrich_media_data(db_instance):
    """
    Finds unique 'unknown' media or media missing rich data, 
    cleans their titles, and fetches data from OMDb.
    """
    client = OMDBClient()
    
    # Get media that is 'unknown' OR missing genre/rating data
    from sqlalchemy import or_
    to_enrich = db_instance.session.query(Media).filter(
        or_(
            Media.media_type == 'unknown',
            Media.genres == None,
            Media.rating == None
        )
    ).all()
    
    # Group by cleaned title first to minimize API calls
    title_groups = {}
    for media in to_enrich:
        base_title = clean_netflix_title(media.title)
        if base_title not in title_groups:
            title_groups[base_title] = []
        title_groups[base_title].append(media)
    
    enriched_count = 0
    for base_title, media_items in title_groups.items():
        data = client.search_by_title(base_title)
        if data:
            for media in media_items:
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
    media.genres = data.get('Genre')
    media.rating = data.get('imdbRating')
    media.runtime = data.get('Runtime')
    
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

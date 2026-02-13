from app import create_app
from database import db
from models import Media, WatchHistory, MediaPerson
from utils.title_cleaner import clean_netflix_title

def deduplicate():
    app = create_app()
    with app.app_context():
        print("Starting deduplication...")
        all_media = Media.query.all()
        title_map = {}
        merged_count = 0
        
        for m in all_media:
            base = clean_netflix_title(m.title)
            
            if base not in title_map:
                # This is the first time we see this series name
                title_map[base] = m
                m.title = base
            else:
                # We already have a record for this series
                target = title_map[base]
                
                # 1. Move Watch History to the main record
                WatchHistory.query.filter_by(media_id=m.id).update({'media_id': target.id})
                
                # 2. Move Person associations (Roles)
                # Since MediaPerson is an association object, we need to handle duplicates
                roles = MediaPerson.query.filter_by(media_id=m.id).all()
                for role in roles:
                    # Check if target already has this person/role
                    exists = MediaPerson.query.filter_by(
                        media_id=target.id, 
                        person_id=role.person_id, 
                        role=role.role
                    ).first()
                    if not exists:
                        role.media_id = target.id
                    else:
                        db.session.delete(role)

                # 3. Delete the duplicate media record
                db.session.delete(m)
                merged_count += 1
                
            if merged_count % 100 == 0 and merged_count > 0:
                db.session.commit()
                print(f"Merged {merged_count} duplicates...")

        db.session.commit()
        print(f"Finished! Total duplicates merged: {merged_count}")

if __name__ == "__main__":
    deduplicate()

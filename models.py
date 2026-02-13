from app import db

# Association table for Many-to-Many relationship between Media and Person
media_people = db.Table('media_people',
    db.Column('media_id', db.Integer, db.ForeignKey('media.id'), primary_key=True),
    db.Column('person_id', db.Integer, db.ForeignKey('person.id'), primary_key=True),
    db.Column('role', db.String(50)) # e.g., 'Actor', 'Director', 'Creator'
)

class Media(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    tmdb_id = db.Column(db.Integer, unique=True, nullable=True)
    title = db.Column(db.String(200), nullable=False)
    media_type = db.Column(db.String(50)) # 'movie' or 'tv'
    release_date = db.Column(db.String(20))
    overview = db.Column(db.Text)
    
    # Relationships
    people = db.relationship('Person', secondary=media_people, backref=db.backref('media_works', lazy='dynamic'))

class Person(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    tmdb_id = db.Column(db.Integer, unique=True, nullable=True)
    name = db.Column(db.String(200), nullable=False)
    profile_path = db.Column(db.String(200)) # URL to image

class WatchHistory(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    media_id = db.Column(db.Integer, db.ForeignKey('media.id'), nullable=False)
    watch_date = db.Column(db.DateTime, server_default=db.func.now())
    platform = db.Column(db.String(50)) # e.g., 'Netflix'
    
    media = db.relationship('Media', backref=db.backref('watch_entries', lazy=True))

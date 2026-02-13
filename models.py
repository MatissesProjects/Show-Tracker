from database import db

class MediaPerson(db.Model):
    __tablename__ = 'media_person'
    media_id = db.Column(db.Integer, db.ForeignKey('media.id'), primary_key=True)
    person_id = db.Column(db.Integer, db.ForeignKey('person.id'), primary_key=True)
    role = db.Column(db.String(50), primary_key=True) # 'Actor', 'Director', 'Creator'
    
    # Relationships to the association object
    person = db.relationship("Person", back_populates="media_memberships")
    media = db.relationship("Media", back_populates="person_memberships")

class Media(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    tmdb_id = db.Column(db.Integer, unique=True, nullable=True)
    title = db.Column(db.String(200), nullable=False)
    media_type = db.Column(db.String(50)) # 'movie' or 'tv'
    release_date = db.Column(db.String(20))
    overview = db.Column(db.Text)
    genres = db.Column(db.String(200))
    rating = db.Column(db.String(10))
    runtime = db.Column(db.String(50))
    user_rating = db.Column(db.Integer, default=0) # 1 for thumbs up, -1 for thumbs down, 0 for neutral
    in_watchlist = db.Column(db.Boolean, default=False)
    
    # Relationship via association object
    person_memberships = db.relationship("MediaPerson", back_populates="media", cascade="all, delete-orphan")

class Person(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    tmdb_id = db.Column(db.Integer, unique=True, nullable=True)
    name = db.Column(db.String(200), nullable=False)
    profile_path = db.Column(db.String(200))
    
    # Relationship via association object
    media_memberships = db.relationship("MediaPerson", back_populates="person", cascade="all, delete-orphan")

class WatchHistory(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    media_id = db.Column(db.Integer, db.ForeignKey('media.id'), nullable=False)
    watch_date = db.Column(db.DateTime, server_default=db.func.now())
    platform = db.Column(db.String(50))
    netflix_sentiment = db.Column(db.String(20)) # 'liked', 'disliked', etc.
    
    media = db.relationship('Media', backref=db.backref('watch_entries', lazy=True))

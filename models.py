from database import db

class MediaPerson(db.Model):
    __tablename__ = 'media_person'
    media_id = db.Column(db.Integer, db.ForeignKey('media.id'), primary_key=True, index=True)
    person_id = db.Column(db.Integer, db.ForeignKey('person.id'), primary_key=True, index=True)
    role = db.Column(db.String(50), primary_key=True) # 'Actor', 'Director', 'Creator'
    
    # Relationships to the association object
    person = db.relationship("Person", back_populates="media_memberships")
    media = db.relationship("Media", back_populates="person_memberships")

class Media(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    tmdb_id = db.Column(db.Integer, unique=True, nullable=True, index=True)
    title = db.Column(db.String(200), nullable=False, index=True)
    media_type = db.Column(db.String(50)) # 'movie' or 'tv'
    release_date = db.Column(db.String(20))
    overview = db.Column(db.Text)
    genres = db.Column(db.String(200))
    rating = db.Column(db.String(10))
    runtime = db.Column(db.String(50))
    total_seasons = db.Column(db.String(20))
    poster_url = db.Column(db.String(500))
    user_rating = db.Column(db.Integer, default=0, index=True) # 2: Love, 1: Like, -1: Dislike, 0: Neutral
    in_watchlist = db.Column(db.Boolean, default=False, index=True)
    ai_insight = db.Column(db.Text)
    
    # Relationship via association object
    person_memberships = db.relationship("MediaPerson", back_populates="media", cascade="all, delete-orphan")

    def to_dict(self):
        return {
            'id': self.id,
            'title': self.title,
            'media_type': self.media_type,
            'release_date': self.release_date,
            'rating': self.rating,
            'genres': self.genres,
            'runtime': self.runtime,
            'total_seasons': self.total_seasons,
            'poster_url': self.poster_url,
            'user_rating': self.user_rating,
            'in_watchlist': self.in_watchlist or False,
            'overview': self.overview,
            'ai_insight': self.ai_insight
        }

class Person(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    tmdb_id = db.Column(db.Integer, unique=True, nullable=True, index=True)
    name = db.Column(db.String(200), nullable=False, index=True)
    profile_path = db.Column(db.String(200))
    
    # Relationship via association object
    media_memberships = db.relationship("MediaPerson", back_populates="person", cascade="all, delete-orphan")

class WatchHistory(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    media_id = db.Column(db.Integer, db.ForeignKey('media.id'), nullable=False, index=True)
    watch_date = db.Column(db.DateTime, server_default=db.func.now(), index=True)
    platform = db.Column(db.String(50))
    netflix_sentiment = db.Column(db.String(20)) # 'liked', 'disliked', etc.
    
    media = db.relationship('Media', backref=db.backref('watch_entries', lazy=True))

class APICache(db.Model):
    __tablename__ = 'api_cache'
    id = db.Column(db.Integer, primary_key=True)
    cache_key = db.Column(db.String(255), unique=True, nullable=False, index=True)
    response_data = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, server_default=db.func.now())
    updated_at = db.Column(db.DateTime, server_default=db.func.now(), onupdate=db.func.now())


import json
from database import db
from models import APICache
from datetime import datetime, timedelta

def get_cached_response(cache_key, expiry_days=30):
    """Retrieves a cached response if it exists and is not expired."""
    try:
        cache_entry = APICache.query.filter_by(cache_key=cache_key).first()
        if cache_entry:
            # Check for expiry if needed, but for media info we generally want to keep it
            if expiry_days:
                expiry_date = cache_entry.updated_at + timedelta(days=expiry_days)
                if datetime.now() > expiry_date:
                    return None
            return json.loads(cache_entry.response_data)
    except Exception as e:
        print(f"Cache retrieval error: {e}")
    return None

def set_cached_response(cache_key, response_data):
    """Stores or updates a response in the cache."""
    try:
        cache_entry = APICache.query.filter_by(cache_key=cache_key).first()
        if cache_entry:
            cache_entry.response_data = json.dumps(response_data)
            cache_entry.updated_at = datetime.now()
        else:
            cache_entry = APICache(
                cache_key=cache_key,
                response_data=json.dumps(response_data)
            )
            db.session.add(cache_entry)
        db.session.commit()
    except Exception as e:
        print(f"Cache storage error: {e}")
        db.session.rollback()

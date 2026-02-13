
from app import create_app
from database import db
from models import Media

app = create_app()
with app.app_context():
    # Items the user has rated but aren't in watchlist
    # In this app, rating an item usually removes it from watchlist (because it's watched)
    # But if the user wants them in the 'Your Watchlist' section specifically:
    
    # Let's find specific titles the user likely wants back
    # Or just assume items with user_rating == 0 and in_watchlist == 1 are what's missing
    
    # Wait, the user said "watchlist is gone". 
    # Let's check for any items that SHOULD be there.
    
    # If they were added manually via 'Discover' but not rated, rating would be 0
    # Let's see if we have ANY rating 0 items
    neutral_items = Media.query.filter_by(user_rating=0).all()
    print(f"Neutral items: {len(neutral_items)}")
    
    # If the user wants their RATED items to also show in watchlist (unlikely but possible)
    # or if they had specific unrated items.
    
    # Let's try to find 'Devs' or 'Better Off Ted' if they were added
    titles_to_watchlist = ['Devs', 'Better Off Ted', 'Lapsis']
    for t in titles_to_watchlist:
        m = Media.query.filter_by(title=t).first()
        if m:
            m.in_watchlist = True
            print(f"Restored {t} to watchlist")
            
    db.session.commit()

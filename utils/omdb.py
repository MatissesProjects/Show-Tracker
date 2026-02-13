import requests
import os
from dotenv import load_dotenv

load_dotenv()

class OMDBClient:
    def __init__(self):
        self.api_key = os.getenv('OMDB_API_KEY')
        self.base_url = "http://www.omdbapi.com/"

    def search_by_title(self, title):
        """Fetch basic info and actors/directors for a title."""
        if not self.api_key or self.api_key == 'your_key_here':
            raise Exception("OMDB_API_KEY not set in .env")
            
        params = {
            'apikey': self.api_key,
            't': title,
            'plot': 'short'
        }
        
        try:
            response = requests.get(self.base_url, params=params)
            response.raise_for_status()
            data = response.json()
            
            if data.get('Response') == 'True':
                return data
            return None
        except Exception as e:
            print(f"Error fetching from OMDb: {e}")
            return None

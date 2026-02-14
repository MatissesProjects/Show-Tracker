
import requests
import json
import os
from dotenv import load_dotenv
from utils.cache import get_cached_response, set_cached_response

load_dotenv()

class AIAnalyst:
    def __init__(self, base_url=None, model="qwen3:8b"):
        self.base_url = (base_url or os.getenv('OLLAMA_URL', 'http://localhost:11434')).rstrip('/')
        self.generate_url = f"{self.base_url}/api/generate"
        self.model = model

    def check_availability(self):
        """Checks if the Ollama server is reachable and configured."""
        if not os.getenv('OLLAMA_URL'):
            return False
        try:
            response = requests.get(self.base_url, timeout=2)
            return response.status_code == 200
        except:
            return False

    def generate_insight(self, media_title, media_data, user_profile, refresh=False):
        """Generates a personalized reasoning for why the user would like a specific media."""
        
        cache_key = f"ai_insight_{media_title.lower().replace(' ', '_')}"
        if not refresh:
            cached = get_cached_response(cache_key, expiry_days=14)
            if cached:
                return cached

        # Format the prompt with user tastes
        loved_genres = list(user_profile.get('genres', {}).keys())[:5]
        top_people = list(user_profile.get('people', {}).keys())[:5]
        
        prompt = f"""
        You are a world-class Media Intelligence Analyst. 
        User Profile:
        - Favorite Genres: {', '.join(loved_genres)}
        - Frequently Watched Talent: {', '.join(top_people)}
        
        Media to Analyze:
        - Title: {media_title}
        - Genre: {media_data.get('Genre')}
        - Plot: {media_data.get('Plot') or media_data.get('summary')}
        - Score: {media_data.get('score')}
        
        Task: Write a 2-sentence 'Intelligence Pitch' explaining why this specific user would love this show/movie. 
        Focus on the overlap between their tastes and the media's DNA. 
        Be professional, witty, and persuasive. Do not use generic phrases.
        Output ONLY the 2 sentences.
        """

        try:
            response = requests.post(
                self.generate_url,
                json={
                    "model": self.model,
                    "prompt": prompt,
                    "stream": False,
                    "options": {
                        "temperature": 0.7,
                        "num_predict": 100
                    }
                },
                timeout=120
            )
            if response.status_code == 200:
                insight = response.json().get('response', '').strip()
                set_cached_response(cache_key, insight)
                return insight
            return "Unable to generate AI insight at this time."
        except Exception as e:
            return f"AI Analyst Offline: {str(e)}"

    def chat_with_library(self, query, library_context, refresh=False):
        """Allows natural language queries over the user's library."""
        
        # Use a hash of the query for caching
        import hashlib
        query_hash = hashlib.md5(query.encode()).hexdigest()
        cache_key = f"ai_chat_{query_hash}"
        
        if not refresh:
            cached = get_cached_response(cache_key, expiry_days=7)
            if cached:
                return cached

        prompt = f"""
        You are an expert media assistant. The user is asking about their media library.
        
        Library Context (Top Items):
        {json.dumps(library_context, indent=2)}
        
        User Query: {query}
        
        Answer the query based on the context. If you don't know, say so. 
        Be concise and helpful.
        """
        
        try:
            response = requests.post(
                self.generate_url,
                json={
                    "model": self.model,
                    "prompt": prompt,
                    "stream": False
                },
                timeout=120
            )
            result = response.json().get('response', '').strip()
            set_cached_response(cache_key, result)
            return result
        except Exception as e:
            return "I'm having trouble accessing your library intelligence right now."


import requests
import json

class AIAnalyst:
    def __init__(self, base_url="http://localhost:11434", model="qwen3:8b"):
        self.base_url = f"{base_url}/api/generate"
        self.model = model

    def generate_insight(self, media_title, media_data, user_profile):
        """Generates a personalized reasoning for why the user would like a specific media."""
        
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
                self.base_url,
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
                return response.json().get('response', '').strip()
            return "Unable to generate AI insight at this time."
        except Exception as e:
            return f"AI Analyst Offline: {str(e)}"

    def chat_with_library(self, query, library_context):
        """Allows natural language queries over the user's library."""
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
                self.base_url,
                json={
                    "model": self.model,
                    "prompt": prompt,
                    "stream": False
                },
                timeout=120
            )
            return response.json().get('response', '').strip()
        except Exception as e:
            return "I'm having trouble accessing your library intelligence right now."

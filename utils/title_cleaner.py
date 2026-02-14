import re

def clean_netflix_title(title):
    """
    Groups episodes into a single series name more aggressively.
    Handles:
    - Series: Season 1: Episode
    - Series: Part 1: Episode
    - Series - Season 1 - Episode
    - Movie (Year)
    """
    # If the title is just an episode number or starts with a colon (malformed CSV data)
    if not title or title.strip().startswith(":") or title.strip().lower().startswith("episode"):
        return ""

    # Remove everything after common separators used for seasons/episodes
    # Matches ": Season", ": Part", ": Volume", " - Season", etc.
    patterns = [
        r'[:\-]\s+Season.*',
        r'[:\-]\s+Part.*',
        r'[:\-]\s+Volume.*',
        r'[:\-]\s+Limited Series.*',
        r'[:\-]\s+Chapter.*',
        r'[:\-]\s+Series.*'
    ]
    
    cleaned = title
    for pattern in patterns:
        cleaned = re.split(pattern, cleaned, flags=re.IGNORECASE)[0]
    
    # Also just split on the first colon if it's likely a series format
    # but keep the whole thing if it's a short title (to avoid breaking movies like "7:19")
    if ":" in cleaned and len(cleaned.split(":")[0]) > 3:
        cleaned = cleaned.split(":")[0]
        
    return cleaned.strip()

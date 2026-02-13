import re

def clean_netflix_title(title):
    """
    Groups episodes into a single series name.
    Example: "Stranger Things: Season 1: Chapter One" -> "Stranger Things"
    Example: "Inception" -> "Inception"
    """
    # Netflix titles often use ":" or " - " to separate series, seasons, and episodes
    # We take everything before the first colon or dash
    parts = re.split(r'[:\-]', title)
    return parts[0].strip()


import requests
import json
from utils.recommender import fetch_by_person

def test():
    profile = {
        'loved_people_ids': [],
        'liked_people_ids': [],
        'disliked_people_ids': [],
        'people': {},
        'genres': {}
    }
    seen = set()
    results = fetch_by_person("H. Jon Benjamin", profile, seen, 5)
    print(f"Results for H. Jon Benjamin: {len(results)}")
    for r in results:
        print(f"- {r['title']}")

if __name__ == "__main__":
    test()


import requests
import json

def fetch_by_person(person_name):
    print(f"Searching for {person_name}...")
    person_res = requests.get(f"https://api.tvmaze.com/search/people?q={person_name}", timeout=5)
    if person_res.ok and person_res.json():
        person = person_res.json()[0]['person']
        person_id = person['id']
        print(f"Found {person['name']} (ID: {person_id})")
        
        cast_res = requests.get(f"https://api.tvmaze.com/people/{person_id}/castcredits?embed=show", timeout=5)
        print(f"Cast status: {cast_res.status_code}")
        if cast_res.ok:
            credits = cast_res.json()
            print(f"Credits count: {len(credits)}")
            for c in credits[:3]:
                print(f"- Show: {c['_embedded']['show']['name']}")
    else:
        print("Person not found")

if __name__ == "__main__":
    fetch_by_person("H. Jon Benjamin")
    fetch_by_person("Alex Garland")

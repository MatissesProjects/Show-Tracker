
import requests
import json

def debug_crew(person_name):
    print(f"Searching for {person_name}...")
    person_res = requests.get(f"https://api.tvmaze.com/search/people?q={person_name}", timeout=5)
    if person_res.ok and person_res.json():
        person = person_res.json()[0]['person']
        person_id = person['id']
        print(f"Found {person['name']} (ID: {person_id})")
        
        crew_res = requests.get(f"https://api.tvmaze.com/people/{person_id}/crewcredits?embed=show", timeout=5)
        print(f"Crew status: {crew_res.status_code}")
        if crew_res.ok:
            credits = crew_res.json()
            print(f"Crew credits count: {len(credits)}")
            for c in credits[:3]:
                print(f"- Show: {c['_embedded']['show']['name']} (Role: {c['type']})")
    else:
        print("Person not found")

if __name__ == "__main__":
    debug_crew("Alex Garland")
    debug_crew("Michael Schur")

import os
import json
import requests
from datetime import datetime, timezone

# Load secrets
CLIENT_ID = os.environ['STRAVA_CLIENT_ID']
CLIENT_SECRET = os.environ['STRAVA_CLIENT_SECRET']
REFRESH_TOKENS_JSON = os.environ['STRAVA_REFRESH_TOKENS']

refresh_tokens = json.loads(REFRESH_TOKENS_JSON)
now = datetime.now(timezone.utc)
month_start = int(datetime(now.year, now.month, 1, tzinfo=timezone.utc).timestamp())

athletes_out = {}

for username, info in refresh_tokens.items():
    print(f"Fetching data for {username}...")
    
    # Refresh token to get access token
    try:
        r = requests.post("https://www.strava.com/oauth/token", data={
            "client_id": CLIENT_ID,
            "client_secret": CLIENT_SECRET,
            "grant_type": "refresh_token",
            "refresh_token": info['refresh_token']
        })
        token_data = r.json()
        access_token = token_data['access_token']
    except Exception as e:
        print(f"Error refreshing token for {username}: {e}")
        continue

    # Fetch athlete profile
    try:
        r = requests.get(
            "https://www.strava.com/api/v3/athlete",
            headers={"Authorization": f"Bearer {access_token}"}
        )
        athlete = r.json()
        if 'message' in athlete:
            print(f"Error fetching profile for {username}: {athlete['message']}")
            continue
    except Exception as e:
        print(f"Error fetching profile for {username}: {e}")
        continue

    # Fetch activities for current month
    try:
        r = requests.get(
            "https://www.strava.com/api/v3/athlete/activities",
            headers={"Authorization": f"Bearer {access_token}"},
            params={"after": month_start, "per_page": 200}
        )
        activities = r.json()

        # If API returned error message instead of list
        if isinstance(activities, dict) and activities.get("message"):
            print(f"Error fetching activities for {username}: {activities['message']}")
            activities = []
        elif not isinstance(activities, list):
            print(f"Unexpected activities response for {username}: {activities}")
            activities = []

    except Exception as e:
        print(f"Error fetching activities for {username}: {e}")
        activities = []

    # Filter leg-based activities
    leg_activities = [a for a in activities if a.get('type') in ['Run','Walk','Hike']]

    # Prepare daily distance array
    daily_distance = [0]*30
    for a in leg_activities:
        try:
            day = datetime.fromisoformat(a['start_date_local']).day - 1
            if 0 <= day < 30:
                daily_distance[day] += a['distance']/1000  # meters to km
        except Exception:
            continue

    athletes_out[username] = {
        "firstname": athlete.get("firstname", ""),
        "lastname": athlete.get("lastname", ""),
        "username": athlete.get("username", ""),
        "profile": athlete.get("profile_medium") or athlete.get("profile") or "",
        "daily_distance_km": daily_distance
    }

# Write updated JSON
os.makedirs("data", exist_ok=True)
with open("data/athletes.json", "w") as f:
    json.dump({"athletes": athletes_out}, f, indent=2)

print("Strava data fetch complete.")

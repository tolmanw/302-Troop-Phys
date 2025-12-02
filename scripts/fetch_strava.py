import os
import json
import requests
from datetime import datetime, timezone

# Load GitHub secrets from environment
CLIENT_ID = os.environ['STRAVA_CLIENT_ID']
CLIENT_SECRET = os.environ['STRAVA_CLIENT_SECRET']
REFRESH_TOKENS_JSON = os.environ['STRAVA_REFRESH_TOKENS']

refresh_tokens = json.loads(REFRESH_TOKENS_JSON)
now = datetime.now(timezone.utc)
month_start = int(datetime(now.year, now.month, 1, tzinfo=timezone.utc).timestamp())

athletes_out = {}

for username, info in refresh_tokens.items():
    # Refresh token to get access token
    r = requests.post("https://www.strava.com/oauth/token", data={
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET,
        "grant_type": "refresh_token",
        "refresh_token": info['refresh_token']
    })
    token_data = r.json()
    access_token = token_data['access_token']

    # Fetch athlete profile
    r = requests.get(
        "https://www.strava.com/api/v3/athlete",
        headers={"Authorization": f"Bearer {access_token}"}
    )
    athlete = r.json()

    # Fetch activities for current month
    r = requests.get(
        "https://www.strava.com/api/v3/athlete/activities",
        headers={"Authorization": f"Bearer {access_token}"},
        params={"after": month_start, "per_page": 200}
    )
    activities = r.json()

    # Filter leg-based activities
    leg_activities = [a for a in activities if a['type'] in ['Run','Walk','Hike']]

    # Prepare daily distance array
    daily_distance = [0]*30
    for a in leg_activities:
        day = datetime.fromisoformat(a['start_date_local']).day - 1
        if 0 <= day < 30:
            daily_distance[day] += a['distance']/1000  # meters to km

    athletes_out[username] = {
        "firstname": athlete.get("firstname"),
        "lastname": athlete.get("lastname"),
        "username": athlete.get("username"),
        "profile": athlete.get("profile_medium") or athlete.get("profile"),
        "daily_distance_km": daily_distance
    }

# Write updated JSON
os.makedirs("data", exist_ok=True)
with open("data/athletes.json", "w") as f:
    json.dump({"athletes": athletes_out}, f, indent=2)

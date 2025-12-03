import os
import json
import requests
from datetime import datetime, timedelta, timezone

# --- Load environment variables ---
CLIENT_ID = os.environ['STRAVA_CLIENT_ID']
CLIENT_SECRET = os.environ['STRAVA_CLIENT_SECRET']
REFRESH_TOKENS_JSON = os.environ['STRAVA_REFRESH_TOKENS']

refresh_tokens = json.loads(REFRESH_TOKENS_JSON)

# --- Helper functions ---
def refresh_access_token(refresh_token):
    response = requests.post(
        "https://www.strava.com/oauth/token",
        data={
            "client_id": CLIENT_ID,
            "client_secret": CLIENT_SECRET,
            "grant_type": "refresh_token",
            "refresh_token": refresh_token
        }
    )
    data = response.json()
    if "access_token" not in data:
        print("Error refreshing token:", data)
        return None
    return data["access_token"]

def get_last_three_month_starts():
    """Return timestamps and datetime objects for the first day of the last 3 months."""
    now = datetime.now(timezone.utc)
    month_starts = []

    for i in range(2, -1, -1):  # 2 months ago, 1 month ago, current
        month = now.month - i
        year = now.year
        if month <= 0:
            month += 12
            year -= 1
        first_day = datetime(year, month, 1, tzinfo=timezone.utc)
        month_starts.append(first_day)

    timestamps = [int(d.timestamp()) for d in month_starts]
    return timestamps, month_starts

def fetch_activities(access_token, after_ts):
    url = "https://www.strava.com/api/v3/athlete/activities"
    params = {"after": after_ts, "per_page": 200}
    headers = {"Authorization": f"Bearer {access_token}"}
    response = requests.get(url, headers=headers, params=params)
    if response.status_code != 200:
        print("Error fetching activities:", response.text)
        return []
    activities = response.json()
    return activities if isinstance(activities, list) else []

# --- Main process ---
athletes_out = {}

prev_ts, month_starts = get_last_three_month_starts()
month_names = [m.strftime("%B %Y") for m in month_starts]

for username, info in refresh_tokens.items():
    print(f"Fetching data for {username}...")
    access_token = refresh_access_token(info["refresh_token"])
    if not access_token:
        continue

    # Get activities since 2 months ago
    activities = fetch_activities(access_token, prev_ts[0])
    print(f"Total activities fetched: {len(activities)}")

    # Filter activities by type
    activity_types = ['Run', 'Trail Run', 'Walk', 'Hike', 'Ride', 'Virtual Ride']
    activities = [a for a in activities if a.get("type") in activity_types]

    # Prepare daily distances and times
    now = datetime.now(timezone.utc)
    days_in_current_month = (datetime(now.year, now.month+1, 1, tzinfo=timezone.utc) - datetime(now.year, now.month, 1, tzinfo=timezone.utc)).days if now.month < 12 else 31
    daily_distance = [0.0]*days_in_current_month
    daily_time = ["0:0"]*days_in_current_month

    monthly_distance = [0.0, 0.0, 0.0]  # 2 previous months + current
    monthly_time = ["0:0","0:0","0:0"]

    for act in activities:
        dt = datetime.strptime(act["start_date_local"], "%Y-%m-%dT%H:%M:%S%z")
        dist_km = act.get("distance",0)/1000
        moving_time = act.get("moving_time",0)  # seconds
        time_hm = f"{moving_time//3600}:{(moving_time%3600)//60}"

        # Assign to months
        for idx, start in enumerate(month_starts):
            if dt.year == start.year and dt.month == start.month:
                monthly_distance[idx] += dist_km
                if idx == 2:  # current month, populate daily
                    daily_distance[dt.day-1] += dist_km
                    daily_time[dt.day-1] = time_hm

    # Fetch athlete profile
    athlete_url = "https://www.strava.com/api/v3/athlete"
    headers = {"Authorization": f"Bearer {access_token}"}
    profile_data = requests.get(athlete_url, headers=headers).json()
    profile_img = profile_data.get("profile","")

    athletes_out[username] = {
        "firstname": profile_data.get("firstname",""),
        "lastname": profile_data.get("lastname",""),
        "username": username,
        "profile": profile_img,
        "monthly_distances": [round(d,2) for d in monthly_distance],
        "daily_distance_km": [round(d,2) for d in daily_distance],
        "monthly_time": monthly_time,
        "daily_time": daily_time
    }

# --- Write JSON ---
os.makedirs("data", exist_ok=True)
with open("data/athletes.json","w") as f:
    json.dump({"athletes":athletes_out,"month_names":month_names},f,indent=2)

print("athletes.json updated successfully.")

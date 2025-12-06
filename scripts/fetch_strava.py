import os
import json
import requests
from datetime import datetime, timedelta, timezone

CLIENT_ID = os.environ['STRAVA_CLIENT_ID']
CLIENT_SECRET = os.environ['STRAVA_CLIENT_SECRET']
REFRESH_TOKENS_JSON = os.environ['STRAVA_REFRESH_TOKENS']

refresh_tokens = json.loads(REFRESH_TOKENS_JSON)

# --- All Strava activity types ---
activity_types = [
    # Foot Sports
    "Run", "Trail Run", "Walk", "Hike", "Virtual Run",
    # Cycle Sports
    "Ride", "Mountain Bike Ride", "Gravel Ride", "E-Bike Ride", "E-Mountain Bike Ride",
    "Velomobile", "Virtual Ride",
    # Water Sports
    "Canoe", "Kayak", "Kitesurf", "Rowing", "Stand Up Paddling", "Surf", "Swim", "Windsurf", "Sail",
    # Winter Sports
    "Ice Skate", "Alpine Ski", "Backcountry Ski", "Nordic Ski", "Snowboard", "Snowshoe",
    # Other Sports
    "Handcycle", "Inline Skate", "Rock Climb", "Roller Ski", "Golf", "Skateboard", "Football (Soccer)",
    "Wheelchair", "Badminton", "Tennis", "Pickleball", "Crossfit", "Elliptical", "Stair Stepper",
    "Weight Training", "Yoga", "Workout", "HIIT", "Pilates", "Table Tennis", "Squash", "Racquetball",
    "Virtual Rowing"
]

# Map real usernames to public aliases
USERNAME_ALIASES = {
    "will_tolman": "TO2388",
    # add more here for other athletes
}

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
    now = datetime.now(timezone.utc)
    month_starts = []
    for i in range(2, -1, -1):
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

def days_in_month(dt):
    next_month = dt.replace(day=28) + timedelta(days=4)
    return (next_month - timedelta(days=next_month.day)).day

# --- Main ---
athletes_out = {}
prev_ts, month_starts = get_last_three_month_starts()
month_names = [m.strftime("%B %Y") for m in month_starts]

for username, info in refresh_tokens.items():
    access_token = refresh_access_token(info["refresh_token"])
    if not access_token:
        continue

    activities = fetch_activities(access_token, prev_ts[0])
    activities = [a for a in activities if a.get("type") in activity_types]

    monthly_distance = [0.0, 0.0, 0.0]
    monthly_time_min = [0.0, 0.0, 0.0]
    daily_distance = []
    daily_time_min = []

    for m in month_starts:
        days = days_in_month(m)
        daily_distance.append([0.0]*days)
        daily_time_min.append([0.0]*days)

    for act in activities:
        dt = datetime.strptime(act["start_date_local"], "%Y-%m-%dT%H:%M:%S%z")
        dist_km = act.get("distance",0)/1000
        time_min = act.get("moving_time",0)/60

        for idx, start in enumerate(month_starts):
            if dt.year == start.year and dt.month == start.month:
                monthly_distance[idx] += dist_km
                monthly_time_min[idx] += time_min
                day_idx = dt.day - 1
                daily_distance[idx][day_idx] += dist_km
                daily_time_min[idx][day_idx] += time_min

    # Fetch profile from Strava
    athlete_url = "https://www.strava.com/api/v3/athlete"
    headers = {"Authorization": f"Bearer {access_token}"}
    profile_data = requests.get(athlete_url, headers=headers).json()
    profile_img = profile_data.get("profile","")

    # Use alias for public display
    alias = USERNAME_ALIASES.get(username, username)

    athletes_out[alias] = {
        "display_name": alias,  # front-end only sees alias
        "profile": profile_img,
        "monthly_distances": [round(d,2) for d in monthly_distance],
        "monthly_time": [round(t) for t in monthly_time_min],
        "daily_distance_km": [[round(d,2) for d in month] for month in daily_distance],
        "daily_time_min": [[round(t) for t in month] for month in daily_time_min]
    }

os.makedirs("data", exist_ok=True)
with open("data/athletes.json","w") as f:
    json.dump({"athletes":athletes_out,"month_names":month_names},f,indent=2)

print("athletes.json updated successfully.")

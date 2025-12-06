import os
import json
import requests
from datetime import datetime, timedelta, timezone

CLIENT_ID = os.environ['STRAVA_CLIENT_ID']
CLIENT_SECRET = os.environ['STRAVA_CLIENT_SECRET']
REFRESH_TOKENS_JSON = os.environ['STRAVA_REFRESH_TOKENS']
ALIASES_JSON = os.environ.get("ATHLETE_ALIASES", "{}")

refresh_tokens = json.loads(REFRESH_TOKENS_JSON)
USERNAME_ALIASES = json.loads(ALIASES_JSON)

# Case-insensitive mapping
USERNAME_ALIASES_LOWER = {k.lower(): v for k, v in USERNAME_ALIASES.items()}

# --- All Strava activity types ---
activity_types = [
    "Run", "Trail Run", "Walk", "Hike", "Virtual Run",
    "Ride", "Mountain Bike Ride", "Gravel Ride", "E-Bike Ride", "E-Mountain Bike Ride",
    "Velomobile", "Virtual Ride",
    "Canoe", "Kayak", "Kitesurf", "Rowing", "Stand Up Paddling", "Surf", "Swim", "Windsurf", "Sail",
    "Ice Skate", "Alpine Ski", "Backcountry Ski", "Nordic Ski", "Snowboard", "Snowshoe",
    "Handcycle", "Inline Skate", "Rock Climb", "Roller Ski", "Golf", "Skateboard", "Football (Soccer)",
    "Wheelchair", "Badminton", "Tennis", "Pickleball", "Crossfit", "Elliptical", "Stair Stepper",
    "Weight Training", "Yoga", "Workout", "HIIT", "Pilates", "Table Tennis", "Squash", "Racquetball",
    "Virtual Rowing"
]

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
        print("Error fetching activities:", response.status_code, response.text)
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

found_athletes = []
skipped_athletes = []

for username, info in refresh_tokens.items():
    access_token = refresh_access_token(info["refresh_token"])
    if not access_token:
        print(f"Failed to refresh token for {username}")
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

    athlete_url = "https://www.strava.com/api/v3/athlete"
    headers = {"Authorization": f"Bearer {access_token}"}
    profile_data = requests.get(athlete_url, headers=headers).json()
    profile_img = profile_data.get("profile","")

    real_name = f"{profile_data.get('firstname','')} {profile_data.get('lastname','')}"
    print(f"Found athlete: '{real_name}'")  # Debug

    alias = USERNAME_ALIASES_LOWER.get(real_name.lower())
    if not alias:
        print(f"Skipping {real_name}: no alias defined")
        skipped_athletes.append(real_name)
        continue

    found_athletes.append(real_name)
    athletes_out[alias] = {
        "display_name": alias,
        "profile": profile_img,
        "monthly_distances": [round(d,2) for d in monthly_distance],
        "monthly_time": [round(t) for t in monthly_time_min],
        "daily_distance_km": [[round(d,2) for d in month] for month in daily_distance],
        "daily_time_min": [[round(t) for t in month] for month in daily_time_min]
    }

os.makedirs("data", exist_ok=True)
with open("data/athletes.json","w") as f:
    json.dump({"athletes":athletes_out,"month_names":month_names},f,indent=2)

print(f"athletes.json updated successfully.")
print(f"Found athletes: {found_athletes}")
print(f"Skipped athletes (no alias): {skipped_athletes}")

import os
import json
import requests
from datetime import datetime, timedelta, timezone
from calendar import monthrange

# --- Load environment variables ---
CLIENT_ID = os.environ['STRAVA_CLIENT_ID']
CLIENT_SECRET = os.environ['STRAVA_CLIENT_SECRET']
REFRESH_TOKENS_JSON = os.environ['STRAVA_REFRESH_TOKENS']

# Parse refresh tokens (JSON mapping username -> { "refresh_token": "..." })
refresh_tokens = json.loads(REFRESH_TOKENS_JSON)

# Activity types to expose
ALLOWED_TYPES = ["Run", "Trail Run", "Walk", "Hike", "Ride", "Virtual Ride"]
ALL_KEY = "All"
TYPES = [ALL_KEY] + ALLOWED_TYPES

def refresh_access_token(refresh_token):
    """Exchange refresh token for access token."""
    r = requests.post(
        "https://www.strava.com/oauth/token",
        data={
            "client_id": CLIENT_ID,
            "client_secret": CLIENT_SECRET,
            "grant_type": "refresh_token",
            "refresh_token": refresh_token
        }
    )
    try:
        data = r.json()
    except Exception:
        print("Failed to parse token response:", r.text)
        return None
    if "access_token" not in data:
        print("Error refreshing token:", data)
        return None
    return data["access_token"]

def get_month_start_dates():
    """Return (previous_month_start_ts, current_month_start_ts, [prev_dt, curr_dt])"""
    now = datetime.now(timezone.utc)
    current_first = datetime(now.year, now.month, 1, tzinfo=timezone.utc)
    prev_last = current_first - timedelta(days=1)
    prev_first = datetime(prev_last.year, prev_last.month, 1, tzinfo=timezone.utc)
    return int(prev_first.timestamp()), int(current_first.timestamp()), [prev_first, current_first]

def fetch_activities(access_token, after_ts):
    """Fetch activities since after_ts (single page per call)."""
    url = "https://www.strava.com/api/v3/athlete/activities"
    params = {"after": after_ts, "per_page": 200}
    headers = {"Authorization": f"Bearer {access_token}"}
    r = requests.get(url, headers=headers, params=params)
    if r.status_code != 200:
        print("Error fetching activities:", r.text)
        return []
    try:
        activities = r.json()
    except Exception:
        print("Failed to parse activities response:", r.text)
        return []
    return activities if isinstance(activities, list) else []

# --- Main ---
prev_ts, curr_ts, month_starts = get_month_start_dates()
month_names = [m.strftime("%B %Y") for m in month_starts]

athletes_out = {}

for username, info in refresh_tokens.items():
    print(f"Fetching data for {username}...")
    refresh_token = info.get("refresh_token")
    if not refresh_token:
        print(f"Missing refresh_token for {username}, skipping.")
        continue

    access_token = refresh_access_token(refresh_token)
    if not access_token:
        print(f"Failed to get access token for {username}, skipping.")
        continue

    # fetch activities since prev month start (covers prev + current)
    activities = fetch_activities(access_token, prev_ts)
    print(f"Total activities fetched: {len(activities)}")

    # prepare containers
    # monthly_per_type: { type: [prev_total_km, curr_total_km], ... }
    monthly_per_type = {t: [0.0, 0.0] for t in TYPES}

    # days in current month
    now = datetime.now(timezone.utc)
    days_in_month = monthrange(now.year, now.month)[1]
    daily_per_type = {t: [0.0]*days_in_month for t in TYPES}

    # iterate activities and bucket by type & month
    for act in activities:
        if not isinstance(act, dict):
            continue
        a_type = act.get("type")
        if a_type not in ALLOWED_TYPES:
            # skip activity types we are not tracking
            continue

        try:
            dist_km = float(act.get("distance", 0)) / 1000.0
        except Exception:
            dist_km = 0.0

        # parse start date local
        try:
            dt = datetime.strptime(act.get("start_date_local"), "%Y-%m-%dT%H:%M:%S%z")
        except Exception:
            # try without tz
            try:
                dt = datetime.strptime(act.get("start_date_local"), "%Y-%m-%dT%H:%M:%S")
            except Exception:
                continue

        # previous month?
        if dt.year == month_starts[0].year and dt.month == month_starts[0].month:
            monthly_per_type[a_type][0] += dist_km
            monthly_per_type[ALL_KEY][0] += dist_km
        # current month?
        if dt.year == month_starts[1].year and dt.month == month_starts[1].month:
            monthly_per_type[a_type][1] += dist_km
            monthly_per_type[ALL_KEY][1] += dist_km
            # daily
            day_idx = dt.day - 1
            if 0 <= day_idx < days_in_month:
                daily_per_type[a_type][day_idx] += dist_km
                daily_per_type[ALL_KEY][day_idx] += dist_km

    # fetch profile
    athlete_profile = {}
    try:
        r = requests.get("https://www.strava.com/api/v3/athlete", headers={"Authorization": f"Bearer {access_token}"})
        athlete_profile = r.json() if isinstance(r.json(), dict) else {}
    except Exception as e:
        print("Failed to fetch profile:", e)
        athlete_profile = {}

    # format output: for each athlete produce monthly_distances map and daily_distance_km map
    # round values to 2 dp
    monthly_out = {t: [round(x,2) for x in monthly_per_type[t]] for t in monthly_per_type}
    daily_out = {t: [round(x,2) for x in daily_per_type[t]] for t in daily_per_type}

    athletes_out[username] = {
        "firstname": athlete_profile.get("firstname", ""),
        "lastname": athlete_profile.get("lastname", ""),
        "username": username,
        "profile": athlete_profile.get("profile_medium") or athlete_profile.get("profile") or "",
        "monthly_distances": monthly_out,
        "daily_distance_km": daily_out
    }

# write JSON
os.makedirs("data", exist_ok=True)
out = {"athletes": athletes_out, "month_names": month_names, "activity_types": TYPES}
with open("data/athletes.json", "w") as f:
    json.dump(out, f, indent=2)

print("athletes.json updated successfully.")

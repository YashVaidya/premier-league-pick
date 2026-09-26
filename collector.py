# data collector process
# pulls PL matches + table from football-data.org, saves to db,
# then drops an event on the queue so the analyzer knows to run

import os
import time
from datetime import datetime

import requests
from dotenv import load_dotenv

from models import Match, Standing, app, bump_metric, db, publish_event, set_metric

load_dotenv()

API = "https://api.football-data.org/v4"
SLEEP_SECONDS = int(os.getenv("COLLECTOR_SLEEP", "3600"))  # hourly is fine, free tier is 10/min


def get_token():
    token = os.getenv("FOOTBALL_DATA_API_TOKEN")
    if not token:
        raise SystemExit("missing FOOTBALL_DATA_API_TOKEN")
    return token


def api_get(path, token):
    r = requests.get(
        API + path,
        headers={"X-Auth-Token": token},
        timeout=30,
    )
    left = r.headers.get("x-requests-available-minute")
    print("api requests left this minute:", left)
    r.raise_for_status()
    return r.json()


def parse_utc(value):
    return datetime.fromisoformat(value.replace("Z", "+00:00")).replace(tzinfo=None)


def save_matches(payload):
    for m in payload.get("matches", []):
        ft = (m.get("score") or {}).get("fullTime") or {}
        # merge so a second collect (or seed + worker) doesnt blow up on pk
        row = Match(
            id=m["id"],
            utc_date=parse_utc(m["utcDate"]),
            status=m.get("status") or "UNKNOWN",
            matchday=m.get("matchday"),
            home_team=m["homeTeam"]["name"],
            away_team=m["awayTeam"]["name"],
            home_score=ft.get("home"),
            away_score=ft.get("away"),
            collected_at=datetime.utcnow(),
        )
        db.session.merge(row)


def save_standings(payload):
    table = []
    for block in payload.get("standings", []):
        if block.get("type") == "TOTAL":
            table = block.get("table") or []
            break
    for row in table:
        team = row["team"]
        existing = Standing.query.filter_by(team_id=team["id"]).first()
        if existing is None:
            existing = Standing(team_id=team["id"])
            db.session.add(existing)
        existing.position = row["position"]
        existing.team_name = team["name"]
        existing.played_games = row["playedGames"]
        existing.won = row["won"]
        existing.draw = row["draw"]
        existing.lost = row["lost"]
        existing.points = row["points"]
        existing.goals_for = row["goalsFor"]
        existing.goals_against = row["goalsAgainst"]
        existing.goal_difference = row["goalDifference"]
        existing.collected_at = datetime.utcnow()


def collect_once(token):
    print("collecting premier league data...")
    matches = api_get("/competitions/PL/matches", token)
    save_matches(matches)
    standings = api_get("/competitions/PL/standings", token)
    save_standings(standings)
    publish_event("collected")
    bump_metric("collect_runs")
    set_metric("last_collect_at", datetime.utcnow().isoformat())
    db.session.commit()
    print("saved", Match.query.count(), "matches,", Standing.query.count(), "standings")
    print("published collected event for analyzer")


def main():
    token = get_token()
    with app.app_context():
        db.create_all()
        while True:
            try:
                collect_once(token)
            except Exception as e:
                print("collect failed:", e)
                bump_metric("collect_errors")
                db.session.commit()
            print("sleeping", SLEEP_SECONDS, "seconds")
            time.sleep(SLEEP_SECONDS)


if __name__ == "__main__":
    main()

# data analyzer process
# waits for "collected" events from the queue, then scores matches
# and writes rankings the web app can show

import os
import time
from datetime import datetime

from dotenv import load_dotenv

from models import Event, Match, Ranking, Standing, app, bump_metric, db, next_event, set_metric
from scoring import score_match

load_dotenv()

SLEEP_SECONDS = int(os.getenv("ANALYZER_SLEEP", "15"))


def upcoming_or_current(matches):
    """prefer not-started games this matchday, else last finished slate"""
    timed = [m for m in matches if m.status in ("SCHEDULED", "TIMED")]
    if timed:
        timed.sort(key=lambda m: m.utc_date)
        # just the next matchday cluster, not the whole rest of the season
        first_md = timed[0].matchday
        same = [m for m in timed if m.matchday == first_md]
        return same or timed[:10]
    finished = [m for m in matches if m.status == "FINISHED"]
    finished.sort(key=lambda m: m.utc_date, reverse=True)
    if not finished:
        return []
    last_md = finished[0].matchday
    return [m for m in finished if m.matchday == last_md]


def analyze_once():
    matches = Match.query.all()
    standings = Standing.query.all()
    if not matches or not standings:
        print("nothing to analyze yet")
        return 0

    slate = upcoming_or_current(matches)
    print("scoring", len(slate), "matches")

    # wipe old rankings so the dashboard is just this slate
    Ranking.query.delete()

    for m in slate:
        scores = score_match(m, matches, standings)
        row = Ranking(
            id=m.id,
            home_team=m.home_team,
            away_team=m.away_team,
            utc_date=m.utc_date,
            status=m.status,
            matchday=m.matchday,
            watch_score=scores["watch_score"],
            form_score=scores["form_score"],
            goals_score=scores["goals_score"],
            stakes_score=scores["stakes_score"],
            reason=scores["reason"],
            analyzed_at=datetime.utcnow(),
        )
        db.session.add(row)

    bump_metric("analyze_runs")
    set_metric("last_analyze_at", datetime.utcnow().isoformat())
    db.session.commit()
    return len(slate)


def process_events():
    handled = 0
    while True:
        event = next_event()
        if event is None:
            break
        print("got event", event.id, event.event_type)
        analyze_once()
        event.processed_at = datetime.utcnow()
        db.session.commit()
        handled += 1
    return handled


def main():
    with app.app_context():
        db.create_all()
        # run once on boot so the site isnt empty if events were missed
        try:
            analyze_once()
        except Exception as e:
            print("startup analyze failed:", e)
        while True:
            try:
                n = process_events()
                if n == 0:
                    # no message this loop, just wait
                    pass
            except Exception as e:
                print("analyze failed:", e)
                bump_metric("analyze_errors")
                db.session.commit()
            time.sleep(SLEEP_SECONDS)


if __name__ == "__main__":
    main()

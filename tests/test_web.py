from datetime import datetime

from analyzer import analyze_once
from models import Match, Ranking, Standing, db


def _seed_for_report():
    db.session.add(Match(
        id=10,
        utc_date=datetime(2026, 9, 6, 13, 0),
        status="TIMED",
        matchday=3,
        home_team="Everton FC",
        away_team="Manchester United FC",
        home_score=None,
        away_score=None,
    ))
    db.session.add(Match(
        id=9,
        utc_date=datetime(2026, 8, 30, 15, 30),
        status="FINISHED",
        matchday=2,
        home_team="Manchester United FC",
        away_team="Ipswich Town FC",
        home_score=5,
        away_score=2,
    ))
    db.session.add(Standing(
        team_id=66, position=11, team_name="Manchester United FC",
        played_games=2, won=1, draw=0, lost=1, points=3,
        goals_for=5, goals_against=4, goal_difference=1,
    ))
    db.session.add(Standing(
        team_id=62, position=8, team_name="Everton FC",
        played_games=2, won=1, draw=1, lost=0, points=4,
        goals_for=3, goals_against=1, goal_difference=2,
    ))
    db.session.add(Standing(
        team_id=349, position=13, team_name="Ipswich Town FC",
        played_games=3, won=1, draw=0, lost=2, points=3,
        goals_for=4, goals_against=8, goal_difference=-4,
    ))
    db.session.add(Standing(
        team_id=57, position=6, team_name="Arsenal FC",
        played_games=2, won=2, draw=0, lost=0, points=6,
        goals_for=4, goals_against=0, goal_difference=4,
    ))
    db.session.commit()


def test_home_form_and_report(client):
    _seed_for_report()
    analyze_once()

    page = client.get("/")
    assert page.status_code == 200
    html = page.get_data(as_text=True)
    assert "PremierLeaguePick" in html
    assert "favorite_team" in html
    assert "Everton FC" in html

    posted = client.post("/", data={"favorite_team": "Manchester United FC"})
    assert posted.status_code == 200
    assert "Highlighting" in posted.get_data(as_text=True)
    assert "Manchester United FC" in posted.get_data(as_text=True)


def test_rest_rankings(client):
    _seed_for_report()
    analyze_once()
    r = client.get("/api/rankings")
    assert r.status_code == 200
    data = r.get_json()
    assert isinstance(data, list)
    assert data[0]["watch_score"] >= 0
    assert "home_team" in data[0]


def test_health_endpoint(client):
    r = client.get("/health")
    assert r.status_code == 200
    body = r.get_json()
    assert body["status"] == "ok"
    assert "metrics" in body


def test_analyze_writes_rankings(client):
    _seed_for_report()
    n = analyze_once()
    assert n >= 1
    assert Ranking.query.count() >= 1

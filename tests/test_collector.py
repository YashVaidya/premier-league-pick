from unittest.mock import Mock, patch

from collector import collect_once
from models import Event, Match, Standing


def _matches_payload():
    return {
        "matches": [
            {
                "id": 1,
                "utcDate": "2026-08-30T15:30:00Z",
                "status": "FINISHED",
                "matchday": 2,
                "homeTeam": {"name": "Manchester United FC"},
                "awayTeam": {"name": "Ipswich Town FC"},
                "score": {"fullTime": {"home": 5, "away": 2}},
            }
        ]
    }


def _standings_payload():
    return {
        "standings": [
            {
                "type": "TOTAL",
                "table": [
                    {
                        "position": 1,
                        "playedGames": 2,
                        "won": 2,
                        "draw": 0,
                        "lost": 0,
                        "points": 6,
                        "goalsFor": 6,
                        "goalsAgainst": 2,
                        "goalDifference": 4,
                        "team": {"id": 65, "name": "Manchester City FC"},
                    }
                ],
            }
        ]
    }


def test_collect_uses_api_and_stores(client):
    # client fixture sets up the test db
    match_resp = Mock()
    match_resp.headers = {"x-requests-available-minute": "8"}
    match_resp.json.return_value = _matches_payload()
    match_resp.raise_for_status.return_value = None

    table_resp = Mock()
    table_resp.headers = {"x-requests-available-minute": "7"}
    table_resp.json.return_value = _standings_payload()
    table_resp.raise_for_status.return_value = None

    with patch("collector.requests.get", side_effect=[match_resp, table_resp]) as mocked:
        collect_once("fake-token")
        assert mocked.call_count == 2
        assert "X-Auth-Token" in mocked.call_args_list[0].kwargs["headers"]

    assert Match.query.count() == 1
    m = Match.query.first()
    assert m.home_team == "Manchester United FC"
    assert m.home_score == 5
    assert Standing.query.count() == 1
    # event queue should have a collected message for the analyzer
    ev = Event.query.filter_by(event_type="collected").first()
    assert ev is not None
    assert ev.processed_at is None

from datetime import datetime

from scoring import avg_goals_for, form_points, last_n_results, score_match, stakes_score


class FakeMatch:
    def __init__(self, home, away, hs, as_, status="FINISHED", when=None, matchday=1):
        self.home_team = home
        self.away_team = away
        self.home_score = hs
        self.away_score = as_
        self.status = status
        self.utc_date = when or datetime(2026, 8, 1)
        self.matchday = matchday


class FakeStanding:
    def __init__(self, name, position, points):
        self.team_name = name
        self.position = position
        self.points = points


def test_form_points_five_wins():
    assert form_points(["W", "W", "W", "W", "W"]) == 1.0


def test_form_points_mixed():
    # W D L = 4 / 9
    assert abs(form_points(["W", "D", "L"]) - (4 / 9)) < 0.001


def test_last_n_results_home_and_away():
    matches = [
        FakeMatch("Arsenal FC", "Everton FC", 3, 0, when=datetime(2026, 8, 10)),
        FakeMatch("Chelsea FC", "Arsenal FC", 1, 1, when=datetime(2026, 8, 17)),
        FakeMatch("Arsenal FC", "Liverpool FC", 0, 2, when=datetime(2026, 8, 24)),
    ]
    assert last_n_results("Arsenal FC", matches) == ["L", "D", "W"]


def test_avg_goals_for():
    matches = [
        FakeMatch("Arsenal FC", "Everton FC", 3, 0, when=datetime(2026, 8, 10)),
        FakeMatch("Chelsea FC", "Arsenal FC", 1, 2, when=datetime(2026, 8, 17)),
    ]
    assert avg_goals_for("Arsenal FC", matches) == 2.5


def test_stakes_top_six_clash():
    table = [
        FakeStanding("Arsenal FC", 1, 12),
        FakeStanding("Liverpool FC", 2, 11),
        FakeStanding("Wolves", 18, 1),
        FakeStanding("Burnley", 6, 9),
        FakeStanding("Fulham", 10, 6),
        FakeStanding("Brentford FC", 7, 8),
    ]
    # add dummy 3-5 so sixth exists
    table[3].position = 6
    score, why = stakes_score("Arsenal FC", "Liverpool FC", table)
    assert score >= 20
    assert "top-six" in why


def test_score_match_returns_all_parts():
    matches = [
        FakeMatch("Arsenal FC", "Everton FC", 3, 0, when=datetime(2026, 8, 10)),
        FakeMatch("Liverpool FC", "Burnley", 4, 1, when=datetime(2026, 8, 10)),
    ]
    table = [
        FakeStanding("Arsenal FC", 1, 12),
        FakeStanding("Liverpool FC", 2, 11),
        FakeStanding("Everton FC", 12, 4),
        FakeStanding("Burnley", 6, 9),
    ]
    upcoming = FakeMatch("Arsenal FC", "Liverpool FC", None, None, status="TIMED", when=datetime(2026, 9, 6))
    out = score_match(upcoming, matches, table)
    assert 0 <= out["watch_score"] <= 100
    assert "form_score" in out and "reason" in out

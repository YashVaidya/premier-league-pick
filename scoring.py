# watchability scoring - kept separate so its easy to unit test
# total is 0-100: form (40) + goals (30) + table stakes (30)


def last_n_results(team_name, matches, n=5):
    """finished matches for a team, newest first, as W/D/L list"""
    played = []
    for m in matches:
        if m.status != "FINISHED":
            continue
        if m.home_team != team_name and m.away_team != team_name:
            continue
        if m.home_score is None or m.away_score is None:
            continue
        played.append(m)
    played.sort(key=lambda x: x.utc_date, reverse=True)
    results = []
    for m in played[:n]:
        if m.home_score == m.away_score:
            results.append("D")
        elif m.home_team == team_name:
            results.append("W" if m.home_score > m.away_score else "L")
        else:
            results.append("W" if m.away_score > m.home_score else "L")
    return results


def form_points(results):
    pts = 0
    for r in results:
        if r == "W":
            pts += 3
        elif r == "D":
            pts += 1
    # 5 games * 3 = 15 max. if fewer games, scale by what we have
    max_pts = max(len(results) * 3, 1)
    return pts / max_pts


def avg_goals_for(team_name, matches, n=5):
    played = []
    for m in matches:
        if m.status != "FINISHED":
            continue
        if m.home_score is None:
            continue
        if m.home_team != team_name and m.away_team != team_name:
            continue
        played.append(m)
    played.sort(key=lambda x: x.utc_date, reverse=True)
    played = played[:n]
    if not played:
        return 1.2  # league-ish default so we dont zero everything
    total = 0
    for m in played:
        if m.home_team == team_name:
            total += m.home_score
        else:
            total += m.away_score
    return total / len(played)


def standing_for(team_name, standings):
    for s in standings:
        if s.team_name == team_name:
            return s
    return None


def stakes_score(home_name, away_name, standings):
    """
    how much the game matters in the table.
    close positions, top 6 fight, or a win punching into top 6.
    """
    home = standing_for(home_name, standings)
    away = standing_for(away_name, standings)
    if home is None or away is None:
        return 12, "table data missing so stakes are a guess"

    gap = abs(home.position - away.position)
    reasons = []
    score = 8

    if home.position <= 6 and away.position <= 6:
        score += 14
        reasons.append("top-six clash")
    elif home.position <= 6 or away.position <= 6:
        score += 8
        reasons.append("a top-six side is involved")

    if gap <= 2:
        score += 10
        reasons.append("they are right next to each other in the table")
    elif gap <= 4:
        score += 6
        reasons.append("the table gap is small")

    # win would put mid-table side into top 6
    for team in (home, away):
        if team.position > 6 and (team.points + 3) >= _sixth_points(standings):
            score += 6
            reasons.append("a win could put a side into the top 6")
            break

    # bottom 3 scrap
    if home.position >= 18 or away.position >= 18:
        score += 6
        reasons.append("relegation scrap")

    score = min(score, 30)
    if not reasons:
        reasons.append("pretty standard table stakes")
    return score, ", ".join(reasons)


def _sixth_points(standings):
    sixth = None
    for s in standings:
        if s.position == 6:
            sixth = s
            break
    return sixth.points if sixth else 999


def score_match(match, matches, standings):
    home_form = last_n_results(match.home_team, matches)
    away_form = last_n_results(match.away_team, matches)
    form = int(round(((form_points(home_form) + form_points(away_form)) / 2) * 40))

    expected_goals = avg_goals_for(match.home_team, matches) + avg_goals_for(match.away_team, matches)
    # 4.0 combined goals ~ max of this bucket
    goals = int(round(min(expected_goals / 4.0, 1.0) * 30))

    stakes, stakes_why = stakes_score(match.home_team, match.away_team, standings)

    total = min(form + goals + stakes, 100)

    bits = []
    bits.append("form " + "-".join(home_form or ["?"]) + " vs " + "-".join(away_form or ["?"]))
    if expected_goals >= 3:
        bits.append("both sides have been scoring")
    bits.append(stakes_why)
    reason = "; ".join(bits)

    return {
        "watch_score": total,
        "form_score": form,
        "goals_score": goals,
        "stakes_score": stakes,
        "reason": reason[:400],
    }

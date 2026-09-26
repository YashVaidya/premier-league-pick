# web process - form + ranked report + rest endpoints
# users only talk to this one

from datetime import datetime

from flask import jsonify, render_template, request

from models import Metric, Ranking, Standing, app, bump_metric, db, set_metric

# gunicorn doesnt run __main__, so make sure tables exist
with app.app_context():
    db.create_all()


@app.before_request
def _count_requests():
    # skip static-ish noise
    if request.path.startswith("/static"):
        return
    try:
        bump_metric("http_requests")
        db.session.commit()
    except Exception:
        db.session.rollback()


@app.route("/", methods=["GET", "POST"])
def home():
    teams = [s.team_name for s in Standing.query.order_by(Standing.team_name)]
    favorite = None
    if request.method == "POST":
        favorite = (request.form.get("favorite_team") or "").strip() or None

    rankings = Ranking.query.order_by(Ranking.watch_score.desc(), Ranking.utc_date.asc()).all()
    standings = Standing.query.order_by(Standing.position.asc()).all()
    return render_template(
        "index.html",
        rankings=rankings,
        standings=standings,
        teams=teams,
        favorite=favorite,
    )


@app.route("/api/rankings")
def api_rankings():
    rows = Ranking.query.order_by(Ranking.watch_score.desc()).all()
    return jsonify([
        {
            "id": r.id,
            "home_team": r.home_team,
            "away_team": r.away_team,
            "utc_date": r.utc_date.isoformat() if r.utc_date else None,
            "status": r.status,
            "matchday": r.matchday,
            "watch_score": r.watch_score,
            "form_score": r.form_score,
            "goals_score": r.goals_score,
            "stakes_score": r.stakes_score,
            "reason": r.reason,
        }
        for r in rows
    ])


@app.route("/api/standings")
def api_standings():
    rows = Standing.query.order_by(Standing.position.asc()).all()
    return jsonify([
        {
            "position": s.position,
            "team_name": s.team_name,
            "played_games": s.played_games,
            "won": s.won,
            "draw": s.draw,
            "lost": s.lost,
            "points": s.points,
            "goals_for": s.goals_for,
            "goals_against": s.goals_against,
            "goal_difference": s.goal_difference,
        }
        for s in rows
    ])


@app.route("/health")
def health():
    # production monitoring / liveness
    metrics = {m.name: m.value for m in Metric.query.all()}
    return jsonify({
        "status": "ok",
        "time": datetime.utcnow().isoformat(),
        "metrics": metrics,
    })


@app.route("/status")
def status_page():
    metrics = Metric.query.order_by(Metric.name).all()
    return render_template("status.html", metrics=metrics)


if __name__ == "__main__":
    with app.app_context():
        db.create_all()
        set_metric("web_started_at", datetime.utcnow().isoformat())
        db.session.commit()
    port = int(__import__("os").getenv("PORT", "5000"))
    app.run(host="0.0.0.0", port=port)

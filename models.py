# shared db models for web / collector / analyzer
# sqlite locally, postgres on heroku if DATABASE_URL is set

import os
from datetime import datetime

from dotenv import load_dotenv
from flask import Flask
from flask_sqlalchemy import SQLAlchemy

load_dotenv()

basedir = os.path.abspath(os.path.dirname(__file__))


def db_uri():
    uri = os.getenv("DATABASE_URL")
    if not uri:
        return "sqlite:///" + os.path.join(basedir, "pl.db")
    # heroku used to give postgres:// which sqlalchemy doesnt like
    if uri.startswith("postgres://"):
        uri = uri.replace("postgres://", "postgresql://", 1)
    # sqlalchemy 2.1 defaults to psycopg v3; we installed psycopg2
    if uri.startswith("postgresql://") and "+psycopg2" not in uri:
        uri = uri.replace("postgresql://", "postgresql+psycopg2://", 1)
    return uri


def create_app():
    app = Flask(__name__)
    app.config["SQLALCHEMY_DATABASE_URI"] = db_uri()
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    app.config["SECRET_KEY"] = os.getenv("SECRET_KEY", "dev-key-not-for-real-prod")
    return app


app = create_app()
db = SQLAlchemy(app)


class Match(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    utc_date = db.Column(db.DateTime, nullable=False)
    status = db.Column(db.String(32), nullable=False)
    matchday = db.Column(db.Integer)
    home_team = db.Column(db.String(120), nullable=False)
    away_team = db.Column(db.String(120), nullable=False)
    home_score = db.Column(db.Integer)
    away_score = db.Column(db.Integer)
    collected_at = db.Column(db.DateTime, default=datetime.utcnow)


class Standing(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    team_id = db.Column(db.Integer, unique=True)
    position = db.Column(db.Integer, nullable=False)
    team_name = db.Column(db.String(120), nullable=False)
    played_games = db.Column(db.Integer, nullable=False)
    won = db.Column(db.Integer, nullable=False)
    draw = db.Column(db.Integer, nullable=False)
    lost = db.Column(db.Integer, nullable=False)
    points = db.Column(db.Integer, nullable=False)
    goals_for = db.Column(db.Integer, nullable=False)
    goals_against = db.Column(db.Integer, nullable=False)
    goal_difference = db.Column(db.Integer, nullable=False)
    collected_at = db.Column(db.DateTime, default=datetime.utcnow)


# analyzer writes these, web reads them
class Ranking(db.Model):
    id = db.Column(db.Integer, primary_key=True)  # same as match id
    home_team = db.Column(db.String(120), nullable=False)
    away_team = db.Column(db.String(120), nullable=False)
    utc_date = db.Column(db.DateTime, nullable=False)
    status = db.Column(db.String(32), nullable=False)
    matchday = db.Column(db.Integer)
    watch_score = db.Column(db.Integer, nullable=False)
    form_score = db.Column(db.Integer, nullable=False)
    goals_score = db.Column(db.Integer, nullable=False)
    stakes_score = db.Column(db.Integer, nullable=False)
    reason = db.Column(db.String(400), nullable=False)
    analyzed_at = db.Column(db.DateTime, default=datetime.utcnow)


# tiny message queue so collector can signal analyzer
# (event collaboration / messaging from the A rubric)
class Event(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    event_type = db.Column(db.String(40), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    processed_at = db.Column(db.DateTime)


# production monitoring - last run times, request counts, errors
class Metric(db.Model):
    name = db.Column(db.String(80), primary_key=True)
    value = db.Column(db.String(200), nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow)


def bump_metric(name, amount=1):
    row = db.session.get(Metric, name)
    if row is None:
        row = Metric(name=name, value="0")
        db.session.add(row)
    try:
        row.value = str(int(row.value) + amount)
    except ValueError:
        row.value = str(amount)
    row.updated_at = datetime.utcnow()


def set_metric(name, value):
    row = db.session.get(Metric, name)
    if row is None:
        row = Metric(name=name, value=str(value))
        db.session.add(row)
    else:
        row.value = str(value)
    row.updated_at = datetime.utcnow()


def publish_event(event_type):
    db.session.add(Event(event_type=event_type))


def next_event():
    return Event.query.filter_by(processed_at=None).order_by(Event.id.asc()).first()

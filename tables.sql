-- schema sketch. create_db.py actually builds these.

CREATE TABLE IF NOT EXISTS match (
    id INTEGER PRIMARY KEY,
    utc_date DATETIME NOT NULL,
    status VARCHAR(32) NOT NULL,
    matchday INTEGER,
    home_team VARCHAR(120) NOT NULL,
    away_team VARCHAR(120) NOT NULL,
    home_score INTEGER,
    away_score INTEGER,
    collected_at DATETIME
);

CREATE TABLE IF NOT EXISTS standing (
    id INTEGER PRIMARY KEY,
    team_id INTEGER UNIQUE,
    position INTEGER NOT NULL,
    team_name VARCHAR(120) NOT NULL,
    played_games INTEGER NOT NULL,
    won INTEGER NOT NULL,
    draw INTEGER NOT NULL,
    lost INTEGER NOT NULL,
    points INTEGER NOT NULL,
    goals_for INTEGER NOT NULL,
    goals_against INTEGER NOT NULL,
    goal_difference INTEGER NOT NULL,
    collected_at DATETIME
);

CREATE TABLE IF NOT EXISTS ranking (
    id INTEGER PRIMARY KEY,
    home_team VARCHAR(120) NOT NULL,
    away_team VARCHAR(120) NOT NULL,
    utc_date DATETIME NOT NULL,
    status VARCHAR(32) NOT NULL,
    matchday INTEGER,
    watch_score INTEGER NOT NULL,
    form_score INTEGER NOT NULL,
    goals_score INTEGER NOT NULL,
    stakes_score INTEGER NOT NULL,
    reason VARCHAR(400) NOT NULL,
    analyzed_at DATETIME
);

-- event queue between collector and analyzer
CREATE TABLE IF NOT EXISTS event (
    id INTEGER PRIMARY KEY,
    event_type VARCHAR(40) NOT NULL,
    created_at DATETIME,
    processed_at DATETIME
);

CREATE TABLE IF NOT EXISTS metric (
    name VARCHAR(80) PRIMARY KEY,
    value VARCHAR(200) NOT NULL,
    updated_at DATETIME
);

# PremierLeaguePick — Final Project Report

CSCA 5028 Applications of Software Architecture for Big Data

## 1. High-level description

PremierLeaguePick helps Premier League fans who cannot watch every match decide which games are actually worth their time. Instead of scanning Google or Flashscore for raw fixtures, the app shows a ranked must-watch matchday report. Each game gets a watchability score from recent form, how often the sides score, and how much the match matters in the table (for example a mid-table game where a win would put a side into the top six).

Users open the web app, optionally pick a favorite club in a form, and get a highlighted report plus the current table. Behind the scenes a collector process fetches official fixture and standings data from the football-data.org REST API, stores it, and publishes an event. A separate analyzer process reads that event, scores the next slate of matches, and writes rankings for the web app to display over REST.

## 2. Whiteboard architecture

```
  User
    |
    |  browser
    v
+---------+          REST JSON           +-----------+
|  WEB    | <--------------------------> |    DB     |
| process |  GET /api/rankings, /health  | Postgres  |
+---------+  POST / favorite team        | / SQLite  |
                                         +-----------+
                                              ^  ^
          cron-ish loop                       |  |
+-----------+  X-Auth-Token   +---------+     |  |
| COLLECTOR | --------------> | football|     |  |
| process   | <-------------- | -data   |     |  |
+-----------+   matches +     +---------+     |  |
      |         standings                     |  |
      |  INSERT event "collected"             |  |
      +---------------------------------------+  |
                                                 |
+-----------+   poll unprocessed events          |
| ANALYZER  | -----------------------------------+
| process   |   write rankings + metrics
+-----------+
```

### Processes / services

- **Web application (frontend + REST):** the only thing a user touches. Serves the HTML form/report and JSON endpoints (`/api/rankings`, `/api/standings`, `/health`). Reads analyzed data from the database. It does not call football-data.org on page load.
- **Data collector (backend worker):** its own long-running process. On a schedule it calls the external REST API, upserts matches and standings, then publishes a `collected` event onto the event table (our message queue).
- **Data analyzer (backend worker):** its own long-running process. It waits for unprocessed events, scores the current/next matchday, and writes `ranking` rows. Users never talk to it directly.
- **Database:** shared persistence for raw data, rankings, the event queue, and monitoring metrics.
- **External API:** football-data.org v4 (token in `X-Auth-Token`).

This matches the course whiteboard: three free-running processes, collector on a schedule, analyzer reading stored data, web only presenting results, REST between frontend and backend, and messaging so analysis is event-driven instead of only polling.

## 3. Design decisions

**Python / Flask.** The course examples and earlier assignments (echo app, data collection) were Flask. Staying on one stack kept the three processes consistent and made Heroku deploy straightforward (`gunicorn` + Procfile).

**SQL (SQLite locally, Postgres in production) instead of NoSQL.** Match results and league tables are relational: a standing row has a fixed set of numeric columns, matches join conceptually to teams, and we query “order by watch_score” or “position = 6” all the time. A documented schema also made unit/integration tests easier. NoSQL would have been nicer for messy nested JSON dumps, but we flatten the API into tables on collect, which is what we actually report on. Heroku’s ephemeral filesystem is why production uses Postgres (`DATABASE_URL`) — SQLite on a dyno would disappear and would not be shared across the three processes.

**Event table as the message queue.** The A-level rubric asks for event collaboration / messaging. We did not want a paid broker just for a class project, so collector inserts an `event` row and analyzer claims it (`processed_at`). That is the same pattern as a queue: producer, consumer, ack. Analyzer also scores once on startup if events were missed.

**Watchability as three buckets (form 40 / goals 30 / stakes 30).** Simple enough to explain in the UI and to unit test without calling any API.

**Token kept in env vars, never in git.** football-data.org is 10 requests/minute on the free tier. The web app never hits it; only the collector does, about twice an hour.

**Heroku + GitHub Actions.** Production environment is a public Heroku URL. CI runs pytest on every push. CD deploys `main` to Heroku only after tests pass.

## 4. System requirements and how they were tested

### User requirements

| ID | Requirement | How tested |
| --- | --- | --- |
| U1 | As a fan, I want a ranked must-watch list so I know which game to put on. | Integration test `test_home_form_and_report` + `/api/rankings`. Manual check of the live site. |
| U2 | As a fan, I want to pick a favorite team so my club is highlighted. | POST `/` with `favorite_team` in `test_home_form_and_report`. |
| U3 | As a fan, I want to see the current table next to the rankings. | Standings rendered on home page; `/api/standings`. |

### System requirements

| ID | Requirement | How tested |
| --- | --- | --- |
| S1 | Collector fetches PL data from an external REST API. | `test_collect_uses_api_and_stores` mocks `requests.get` and asserts the URL/header + rows saved. |
| S2 | Collected data is persisted. | Same test; also `pl.db` / Postgres after `seed.py`. |
| S3 | Analyzer computes watchability from stored data (not a raw redisplay). | Unit tests in `test_scoring.py`; `test_analyze_writes_rankings`. |
| S4 | Collector and analyzer are separate processes that collaborate via events. | Collector test asserts a `collected` event is published; analyzer consumes `Event` rows. |
| S5 | Web talks to backend data over REST. | `test_rest_rankings`, `test_health_endpoint`. |
| S6 | App is hosted in a production environment. | Deployed to Heroku (`web`, `collector`, `analyzer` dynos). |
| S7 | Unit tests and integration tests exist; HTTP to the API is mocked. | `pytest` in CI. |
| S8 | Production monitoring is instrumented. | `/health` and `/status` expose collect/analyze/http counters. |
| S9 | Continuous integration and delivery. | `.github/workflows/ci.yml` — test job, then Heroku deploy on `main`. |

## 5. Rubric mapping (A level)

| Rubric item | Where it lives |
| --- | --- |
| Web application basic form, reporting | `web_app.py`, `templates/index.html` |
| Data collection | `collector.py` |
| Data analyzer | `analyzer.py`, `scoring.py` |
| Unit tests | `tests/test_scoring.py` |
| Data persistence | SQLite / Postgres, `models.py`, `tables.sql` |
| REST collaboration | `/api/rankings`, `/api/standings`, `/health` |
| Product environment | Heroku Procfile, public URL |
| Integration tests | `tests/test_web.py` |
| Mocks / fakes / spies | `tests/test_collector.py` (`unittest.mock.patch` on `requests.get`) |
| Continuous integration | GitHub Actions `test` job |
| Production monitoring | `Metric` model, `/health`, `/status` |
| Event collaboration messaging | `Event` queue table, `publish_event` / `next_event` |
| Continuous delivery | GitHub Actions `deploy` job after tests |

## 6. How to run

See `README.md`. Short version: `create_db.py`, `seed.py`, then `web_app.py`. Workers: `collector.py` and `analyzer.py` in their own terminals / dynos.

# PremierLeaguePick

This is my final project for the class. It’s a site for Premier League fans who don’t have time to watch every game. Instead of googling fixtures every weekend, you open the dashboard and it ranks the next matchday by how “watchable” a game is.

Watchable meaning: are the teams in form, do they score a lot, and does the game actually matter in the table. Like two mid-table sides that would normally get skipped, but if they both score freely and a win puts someone in the top 6, that should be high on the list. That’s the whole point. I’m not just reprinting Flashscore.

You can also pick a favorite team in the form and those rows get highlighted.

## Architecture

I did it like the whiteboard video. Three different processes, not one app doing everything.

```
user --> web app (the only thing you click on)
              |
              | REST (/api/rankings, /api/standings)
              v
           database
           (sqlite on my laptop, postgres on heroku)
              ^
              |
collector ----+---- analyzer

collector talks to football-data.org
then it drops a "collected" event in an events table
analyzer sees that event and writes the watch scores
```

- **web** — form + the ranked report + a couple json endpoints. users never talk to the other two.
- **collector** — its own process. wakes up, hits the football-data.org api (needs the X-Auth-Token header), saves matches and the table.
- **analyzer** — also its own process. waits for the event, scores the next slate, saves rankings.

I used an events table as the message queue instead of paying for rabbit/redis. Collector inserts a row, analyzer marks it processed. Same idea as a queue, just cheaper.

## Why I picked this stuff

I stuck with **python / flask** because that’s what the course examples used and what I already had from the echo app and the data collection assignment.

**sql not nosql.** the data is basically a league table and a list of matches. columns are the same every time (points, gd, scores). sqlite locally, postgres on heroku because heroku’s filesystem is temporary and the three processes need to share one db.

**token in an env var** not in the repo. free tier is 10 calls a minute so the web page does not call the api, only the collector does.

**heroku + github actions.** public url for the “production environment” thing. tests run on push, then it deploys main if they pass.

Watch score is just form/40 + goals/30 + stakes/30. easy to test without hitting the api.

## Requirements and how I tested them

User stuff:
- see a ranked must-watch list — that’s the home page. I also have a test that loads it.
- pick a favorite team and see it highlighted — the form POST. tested that too.
- see the current table next to it — same page.

System stuff:
- pull from an outside rest api — collector, mocked `requests.get` in tests so I’m not burning the real token in ci
- save it in a db — matches / standings tables
- actually analyze, not just redisplay — scoring.py + analyzer
- three processes, events between collector and analyzer
- rest endpoints for the report
- hosted on heroku
- unit tests, integration tests, mocks
- /health and /status for monitoring
- ci/cd in `.github/workflows/ci.yml`

Live url: https://premier-league-pick-79191efa805b.herokuapp.com/

To run it locally: `python create_db.py`, `python seed.py`, then `python web_app.py`. Collector and analyzer are separate commands if you want the workers.

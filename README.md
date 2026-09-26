# PremierLeaguePick

Ranks Premier League games by watchability (form, goals, table stakes).

Three separate processes:

- `collector.py` — pulls matches/standings from football-data.org
- `analyzer.py` — reads the event queue, scores games, writes rankings
- `web_app.py` — form + report + REST

## local

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
# put FOOTBALL_DATA_API_TOKEN in .env

python create_db.py
python seed.py          # one collect + analyze
python web_app.py       # http://127.0.0.1:5000

# in other terminals if you want the long-running workers:
# python collector.py
# python analyzer.py
```

## tests

```bash
pytest -q
```

## heroku

Procfile starts `web`, `collector`, `analyzer`. CI on GitHub Actions, CD deploys main after tests pass.

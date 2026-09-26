# one-shot collect + analyze so the dashboard isnt empty
# heroku release / first deploy can call this

from analyzer import analyze_once
from collector import collect_once, get_token
from models import app, db


def main():
    with app.app_context():
        db.create_all()
        collect_once(get_token())
        analyze_once()
        print("seed done")


if __name__ == "__main__":
    main()

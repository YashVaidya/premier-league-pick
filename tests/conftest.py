import os
import sys
import tempfile

_db = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
os.environ["DATABASE_URL"] = "sqlite:///" + _db.name
os.environ["FOOTBALL_DATA_API_TOKEN"] = "fake-token"

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

import pytest  # noqa: E402

from models import app, db  # noqa: E402
import web_app  # noqa: E402,F401  # registers routes on app


@pytest.fixture
def client():
    with app.app_context():
        db.drop_all()
        db.create_all()
        yield app.test_client()
        db.session.remove()
        db.drop_all()

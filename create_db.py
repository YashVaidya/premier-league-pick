from models import app, db

with app.app_context():
    db.create_all()
    print("tables ready")

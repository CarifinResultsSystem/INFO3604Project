from backend.App.database import db

def initialize():
    db.drop_all()
    db.create_all()
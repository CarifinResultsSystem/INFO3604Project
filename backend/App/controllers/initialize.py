from backend.App.database import db
from .user import create_user

def initialize():
    db.drop_all()
    db.create_all()
    create_user('bob', 'bobpass')
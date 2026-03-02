from App.database import db
from .user import create_user

def initialize():
    db.drop_all()
    db.create_all()
    create_user('bob', 'admin', 'bob@mail.com', 'bobpass')
    create_user('alice', 'judge', 'alice@mail.com', 'alicepass')
    create_user('john', 'scoretaker', 'john@mail.com', 'johnpass')

from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate


db = SQLAlchemy()

def get_migrate(app):
    return Migrate(app, db)

def create_db():
    db.create_all()
    
def init_db(app):
    uri = app.config.get('SQLALCHEMY_DATABASE_URI', '')
    if uri.startswith('postgres://'):
        app.config['SQLALCHEMY_DATABASE_URI'] = uri.replace('postgres://', 'postgresql://', 1)
    
    db.init_app(app)
    print("DATABASE URI:", app.config.get('SQLALCHEMY_DATABASE_URI'))
    with app.app_context():
        db.create_all()
        seed_db()

def seed_db():
    from App.models import User
    if not User.query.filter_by(username='bob').first():
        admin = User(username='bob', role='admin', email='bob@mail.com', password='bobpass')
        db.session.add(admin)
        db.session.commit()

    if not User.query.filter_by(username='alice').first():
        user = User(username='alice', role='judge', email='alice@mail.com', password='alicepass')
        db.session.add(user)
        db.session.commit()

    if not User.query.filter_by(username='john').first():
        admin = User(username='john', role='scoretaker', email='john@mail.com', password='johnpass')
        db.session.add(admin)
        db.session.commit()

    if not User.query.filter_by(username='eve').first():
        user = User(username='eve', role='hr', email='eve@mail.com', password='evepass')
        db.session.add(user)
        db.session.commit()
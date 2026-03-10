from uuid import uuid4

from App.database import db
from .user import create_user
from .participant import create_participant
from .institution import create_institution
from .pointsRules import create_individual_rule, create_team_rule
from .event import create_event
from .season import create_season

def initialize():
    db.drop_all()
    db.create_all()
    create_user('bob', 'admin', 'bob@mail.com', 'bobpass')
    create_user('alice', 'judge', 'alice@mail.com', 'alicepass')
    create_user('john', 'scoretaker', 'john@mail.com', 'johnpass')
    create_user('eve', 'hr', 'eve@mail.com', 'evepass')
    season = create_season(2026)
    create_institution("Scotiabank", "Port of Spain")
    create_institution("Central Bank of T&T", "Port of Spain")
    create_institution("First Citizens", "Port of Spain")
    create_institution("Ministry of Finance", "Port of Spain")
    create_institution("Sagicor", "Port of Spain")
    create_institution("Trinidad and Tobago Mortage Bank", "Port of Spain")
    create_institution("Trinidad and Tobago Unit Trust Corporation", "Port of Spain")
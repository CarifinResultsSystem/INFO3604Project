from sqlalchemy.exc import IntegrityError
from App.models import Leaderboard, Institution
from App.database import db

def create_leaderboard(year):
    year = int(year)

    existing = db.session.execute(
        db.select(Leaderboard).filter_by(year=year)
    ).scalar_one_or_none()

    if existing:
        return existing

    newLeaderboard = Leaderboard(year=year)
    db.session.add(newLeaderboard)
    db.session.commit()
    return newLeaderboard

def get_leaderboard(year):
    year = int(year)
    return db.session.execute(
        db.select(Leaderboard).filter_by(year=year)
    ).scalar_one_or_none()

def get_institution_list_descending():
    institutions = db.select(Institution).order_by(Institution.insTotalPoints.desc())
    rank = 1
    for ins in institutions:
        institution = db.session.get(Institution, ins)
        institution.insRank = rank
        rank = rank + 1
        db.session.commit()
    return institutions #Updates ranks and gets institution list
    
    
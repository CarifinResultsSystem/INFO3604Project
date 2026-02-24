from App.models import Leaderboard, Institution
from App.database import db

def create_leaderboard(year):
    newLeaderboard = Leaderboard(year=year)
    db.session.add(newLeaderboard)
    db.session.commit()
    return newLeaderboard

def get_leaderboard(year):
    return db.session.get(Leaderboard, year)

def get_institution_list_descending():
    institutions = db.select(Institution).order_by(Institution.insTotalPoints.dsc())
    rank = 1
    for ins in institutions:
        institution = db.session.get(Institution, ins)
        institution.insRank = rank
        rank = rank + 1
        db.session.commit()
    return institutions #Updates ranks and gets institution list
    
    
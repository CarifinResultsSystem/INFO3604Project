from App.database import db

class Leaderboard(db.Model):
    __tablename__ = "leaderboards"

    leaderboardID = db.Column(db.Integer, primary_key=True)
    year = db.Column(db.Integer, nullable=False, unique=True)

    def __init__(self, year):
        self.year = int(year)
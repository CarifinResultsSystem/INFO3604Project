from App.database import db


class Leaderboard(db.Model):
    leaderboardID = db.Column(db.Integer, primary_key=True)
    year = db.Column(db.Date, nullable=False)
    
    def __init__(self, year):
        self.year = year
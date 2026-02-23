from App.database import db


class Season(db.Model):
    __tablename__ = "seasons"

    seasonID = db.Column(db.Integer, primary_key=True)
    year = db.Column(db.Integer, nullable=False, unique=True)

    # Relationship to Leaderboard (if your leaderboard model exists)
    leaderboards = db.relationship(
        "Leaderboard",
        backref="season",
        lazy=True,
        cascade="all, delete-orphan"
    )

    def __init__(self, year: int):
        self.year = year

    def get_json(self):
        return {
            "seasonID": self.seasonID,
            "year": self.year
        }

    @staticmethod
    def get_by_id(season_id: int):
        return db.session.get(Season, season_id)

    @staticmethod
    def get_by_year(year: int):
        return Season.query.filter_by(year=year).first()

    @staticmethod
    def get_all():
        return Season.query.all()
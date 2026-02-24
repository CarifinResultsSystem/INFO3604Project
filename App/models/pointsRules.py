from App.database import db


class PointsRules(db.Model):
    __tablename__ = "points_rules"

    pointsID = db.Column(db.Integer, primary_key=True)

    eventType = db.Column(db.String(100), nullable=False)
    conditionType = db.Column(db.String(100), nullable=False)
    conditionValue = db.Column(db.Integer, nullable=False)

    upperLimit = db.Column(db.Integer, nullable=False)
    lowerLimit = db.Column(db.Integer, nullable=False)

    seasonID = db.Column(
        db.Integer,
        db.ForeignKey("seasons.seasonID"),
        nullable=False
    )

    season = db.relationship(
        "Season",
        backref=db.backref("points_rules", lazy=True, cascade="all, delete-orphan"),
        lazy=True,
    )
    
    automated_results = db.relationship(
        "AutomatedResult",
        backref="points_rule",
        lazy=True
    )

    def __init__(self, eventType, conditionType, conditionValue, upperLimit, lowerLimit, seasonID):
        self.eventType = eventType
        self.conditionType = conditionType
        self.conditionValue = conditionValue
        self.upperLimit = upperLimit
        self.lowerLimit = lowerLimit
        self.seasonID = seasonID

    def get_json(self):
        return {
            "pointsID": self.pointsID,
            "eventType": self.eventType,
            "conditionType": self.conditionType,
            "conditionValue": self.conditionValue,
            "upperLimit": self.upperLimit,
            "lowerLimit": self.lowerLimit,
            "seasonID": self.seasonID
        }
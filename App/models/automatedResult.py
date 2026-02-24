from datetime import datetime
from App.database import db


class AutomatedResult(db.Model):
    __tablename__ = "automated_results"

    resultID = db.Column(db.Integer, primary_key=True)

    score = db.Column(db.Float, nullable=False)
    numErrors = db.Column(db.Integer, default=0)
    errorType = db.Column(db.String(100))
    errorDescription = db.Column(db.String(500))
    errorCorrection = db.Column(db.String(500))

    confirmed = db.Column(db.Boolean, default=False)

    createdAt = db.Column(db.DateTime, default=datetime.utcnow)


    participantID = db.Column(
        db.String(50),
        db.ForeignKey("participants.participantID"),
        nullable=False
    )

    eventID = db.Column(
        db.Integer,
        db.ForeignKey("event.eventID"),
        nullable=False
    )

    pointsID = db.Column(
        db.Integer,
        db.ForeignKey("points_rules.pointsID"),
        nullable=False
    )

    participant = db.relationship(
        "Participant",
        backref=db.backref("automated_results", lazy=True, cascade="all, delete-orphan"),
        lazy=True
    )

    event = db.relationship(
        "Event",
        backref=db.backref("automated_results", lazy=True, cascade="all, delete-orphan"),
        lazy=True
    )

    def __init__(self, score, participantID, eventID, pointsID):
        self.score = score
        self.participantID = participantID
        self.eventID = eventID
        self.pointsID = pointsID

    def get_json(self):
        return {
            "resultID": self.resultID,
            "score": self.score,
            "numErrors": self.numErrors,
            "errorType": self.errorType,
            "errorDescription": self.errorDescription,
            "errorCorrection": self.errorCorrection,
            "confirmed": self.confirmed,
            "participantID": self.participantID,
            "participantName": f"{self.participant.firstName} {self.participant.lastName}" if self.participant else None,
            "eventID": self.eventID,
            "eventName": self.event.eventName if self.event else None,
            "pointsID": self.pointsID,
            "createdAt": self.createdAt.isoformat() if self.createdAt else None
        }
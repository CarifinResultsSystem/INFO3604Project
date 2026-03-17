
from App.database import db

challenge_events = db.Table(
    "challenge_events",
    db.Column(
        "challengeID",
        db.Integer,
        db.ForeignKey("challenges.challengeID", ondelete="CASCADE"),
        primary_key=True,
    ),
    db.Column(
        "eventID",
        db.Integer,
        db.ForeignKey("events.eventID", ondelete="CASCADE"),
        primary_key=True,
    ),
)

challenge_participants = db.Table(
    "challenge_participants",
    db.Column(
        "challengeID",
        db.Integer,
        db.ForeignKey("challenges.challengeID", ondelete="CASCADE"),
        primary_key=True,
    ),
    db.Column(
        "participantID",
        db.String(36),
        db.ForeignKey("participants.participantID", ondelete="CASCADE"),
        primary_key=True,
    ),
)


class Challenge(db.Model):
    __tablename__ = "challenges"

    challengeID   = db.Column(db.Integer, primary_key=True, autoincrement=True)
    challengeName = db.Column(db.String(200), nullable=False, unique=True)
    description   = db.Column(db.String(500), nullable=True)

    seasonID = db.Column(
        db.Integer,
        db.ForeignKey("seasons.seasonID", ondelete="SET NULL"),
        nullable=True,
    )

    bonusPoints = db.Column(db.Float, nullable=False, default=0.0)

    season = db.relationship(
        "Season",
        backref=db.backref("challenges", lazy=True),
    )

    events = db.relationship(
        "Event",
        secondary=challenge_events,
        backref=db.backref("challenges", lazy=True),
        lazy="subquery",
    )

    participants = db.relationship(
        "Participant",
        secondary=challenge_participants,
        backref=db.backref("challenges", lazy=True),
        lazy="subquery",
    )
    
    points_rules = db.relationship(
        "PointsRules",
        backref="challenge",
        lazy=True,
        cascade="all, delete-orphan",
        foreign_keys="PointsRules.challengeID",
    )

    def __init__(self, challengeName, seasonID=None, description=None, bonusPoints=0.0):
        self.challengeName = challengeName
        self.seasonID      = seasonID
        self.description   = description
        self.bonusPoints   = bonusPoints

    def get_json(self):
        return {
            "challengeID":   self.challengeID,
            "challengeName": self.challengeName,
            "description":   self.description,
            "seasonID":      self.seasonID,
            "bonusPoints":   self.bonusPoints,
            "eventIDs":      [e.eventID for e in self.events],
            "participantIDs":[p.participantID for p in self.participants],
        }
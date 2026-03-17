from App.database import db


class PointsRules(db.Model):
    __tablename__ = "points_rules"

    pointsID = db.Column(db.Integer, primary_key=True)
    seasonID = db.Column(db.Integer, db.ForeignKey("seasons.seasonID"),  nullable=False)
    ruleType = db.Column(db.String(20),  nullable=False)
    placement = db.Column(db.Integer,     nullable=True)
    category = db.Column(db.String(150), nullable=True)
    label = db.Column(db.String(255), nullable=True)
    points = db.Column(db.Float,       nullable=False, default=0)
    eventID = db.Column(
        db.Integer,
        db.ForeignKey("events.eventID", ondelete="CASCADE"),
        nullable=True,
    )
    challengeID = db.Column(
        db.Integer,
        db.ForeignKey("challenges.challengeID", ondelete="CASCADE"),
        nullable=True,
    )

    event = db.relationship(
        "Event",
        backref=db.backref("points_rules", lazy=True, cascade="all, delete-orphan"),
        foreign_keys=[eventID],
    )
    season = db.relationship(
        "Season",
        backref=db.backref("points_rules", lazy=True, cascade="all, delete-orphan"),
    )
    automated_results = db.relationship(
        "AutomatedResult",
        backref="points_rule",
        lazy=True,
    )

    def __init__(
        self,
        seasonID,
        ruleType,
        points=0,
        label=None,
        placement=None,
        category=None,
        eventID=None,
        challengeID=None,
    ):
        self.seasonID    = seasonID
        self.ruleType    = ruleType
        self.points      = points
        self.label       = label
        self.placement   = placement
        self.category    = category
        self.eventID     = eventID
        self.challengeID = challengeID
 
    def get_json(self):
        return {
            "pointsID":    self.pointsID,
            "eventID":     self.eventID,
            "challengeID": self.challengeID,
            "seasonID":    self.seasonID,
            "ruleType":    self.ruleType,
            "placement":   self.placement,
            "category":    self.category,
            "label":       self.label,
            "points":      self.points,
        }
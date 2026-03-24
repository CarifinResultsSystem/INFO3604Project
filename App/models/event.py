from App.database import db

class Event(db.Model):
    __tablename__ = "events"
    eventID   = db.Column(db.Integer, primary_key=True)
    eventName = db.Column(db.String(256), nullable=False)
    eventDate = db.Column(db.Date, nullable=False)
    time      = db.Column(db.Time, nullable=False)
    location  = db.Column(db.String(256), nullable=False)
    seasonID  = db.Column(db.Integer, db.ForeignKey("seasons.seasonID"), nullable=False)

    season = db.relationship("Season", backref=db.backref("events", lazy=True))

    def __init__(self, eventName, eventDate, time, location, seasonID):
        self.eventName = eventName
        self.eventDate = eventDate
        self.time      = time
        self.location  = location
        self.seasonID  = seasonID
    
    @property
    def participant_count(self):
        return len(self.participants)

    def get_json(self):
        return {
            "eventID":   self.eventID,
            "eventName": self.eventName,
            "eventDate": self.eventDate.isoformat(),
            "time":      self.time.strftime("%H:%M"),
            "location":  self.location,
            "seasonID":  self.seasonID,
            "year":      self.season.year if self.season else None,
            "participantCount": self.participant_count,
        }
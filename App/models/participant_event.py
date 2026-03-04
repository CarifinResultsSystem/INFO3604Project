from App.database import db

participant_events = db.Table(
    "participant_events",
    db.Column("participantID", db.String(50), db.ForeignKey("participants.participantID"), primary_key=True),
    db.Column("eventID", db.Integer, db.ForeignKey("events.eventID"), primary_key=True)
)
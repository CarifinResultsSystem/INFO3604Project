from App.database import db

class Event(db.Model):
    eventID = db.Column(db.Integer, primary_key=True)
    eventName = db.Column(db.String(256), nullable=False)
    eventDate = db.Column(db.Date, nullable=False)
    time = db.Column(db.Time, nullable=False)
    location = db.Column(db.String(256), nullable=False)
    
    def __init__(self, eventName, eventDate, time, location):
        self.eventName = eventName
        self.eventDate = eventDate
        self.time = time
        self.location = location
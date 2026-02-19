from backend.App.models import User, Event
from backend.App.database import db

def assignRole(userID, role):
    user = db.session.get(User, userID)
    user.role = role
    return None
    #function is subject to change with User Scripts

def createEvent(eventName, eventDate, eventTime, eventLocation):
    newEvent = Event(eventName=eventName, 
                    eventDate=eventDate,
                    time=eventTime,
                    location=eventLocation)
    db.session.add(newEvent)
    db.session.commit()
    return newEvent
        
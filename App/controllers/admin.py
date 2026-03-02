from App.models import User, Event
from App.database import db

def assignRole(userID, role):
    user = db.session.get(User, userID)
    if(role in user.ALLOWED_ROLES):
        user.role = role
        db.session.commit()
        return role
    else:
        return None

def createEvent(eventName, eventDate, eventTime, eventLocation):
    newEvent = Event(eventName=eventName, 
                    eventDate=eventDate,
                    time=eventTime,
                    location=eventLocation)
    db.session.add(newEvent)
    db.session.commit()
    return newEvent
        
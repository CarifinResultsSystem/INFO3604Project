from sqlalchemy.exc import IntegrityError
from App.models import User, Event
from App.database import db
from datetime import datetime

def assignRole(userID, role):
    user = db.session.get(User, userID)
    if not user:
        return None

    role = (role or "").strip().lower()

    allowed = getattr(User, "ALLOWED_ROLES", ["admin", "scoretaker", "judge", "hr", "user"])
    if role not in allowed:
        return None

    user.role = role

    try:
        db.session.commit()
        return user.role
    except IntegrityError:
        db.session.rollback()
        return None

def createEvent(eventName, eventDate, eventTime, eventLocation):
    if not eventName or not str(eventName).strip():
        return None

    newEvent = Event(
        eventName=str(eventName).strip(),
        eventDate=eventDate,
        time=eventTime,
        location=eventLocation
    )

    db.session.add(newEvent)
    try:
        db.session.commit()
        return newEvent
    except IntegrityError:
        db.session.rollback()
        return None
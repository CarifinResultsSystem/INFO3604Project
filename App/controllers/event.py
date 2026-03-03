from datetime import datetime
from App.database import db
from App.models import Event


def get_json(eventID: int):
    event = db.session.get(Event, eventID)
    if not event:
        return None
    return {
        "eventID": event.eventID,
        "eventName": event.eventName,
        "eventDate": event.eventDate.isoformat(),
        "time": event.time.strftime("%H:%M"),
        "location": event.location,
    }


def create_event(eventName: str, eventDate: str, eventTime: str, eventLocation: str):
    if not eventName or not eventLocation:
        return None, "Event name and location are required."

    try:
        date_obj = datetime.strptime(eventDate, "%Y-%m-%d").date()
    except Exception:
        return None, "Invalid date. Use YYYY-MM-DD."

    try:
        time_obj = datetime.strptime(eventTime, "%H:%M").time()
    except Exception:
        return None, "Invalid time. Use HH:MM (24h)."

    new_event = Event(
        eventName=eventName.strip(),
        eventDate=date_obj,
        time=time_obj,
        location=eventLocation.strip(),
    )
    db.session.add(new_event)
    db.session.commit()
    return new_event, None


def delete_event(event_id: int):
    ev = db.session.get(Event, event_id)
    if not ev:
        return False
    db.session.delete(ev)
    db.session.commit()
    return True


def update_event(event_id: int, eventName: str, eventDate: str, eventTime: str, eventLocation: str):
    ev = db.session.get(Event, event_id)
    if not ev:
        return None, "Event not found."

    if not eventName or not eventLocation:
        return None, "Event name and location are required."

    try:
        ev.eventDate = datetime.strptime(eventDate, "%Y-%m-%d").date()
    except Exception:
        return None, "Invalid date. Use YYYY-MM-DD."

    try:
        ev.time = datetime.strptime(eventTime, "%H:%M").time()
    except Exception:
        return None, "Invalid time. Use HH:MM (24h)."

    ev.eventName = eventName.strip()
    ev.location = eventLocation.strip()
    db.session.commit()
    return ev, None
from datetime import datetime
from App.database import db
from App.models import Event, Season


def get_json(eventID: int):
    event = db.session.get(Event, eventID)
    if not event:
        return None
    return event.get_json()


def create_event(eventName: str, eventDate: str, eventTime: str, eventLocation: str, seasonID: int):
    if not eventName or not eventLocation:
        return None, "Event name and location are required."

    if not seasonID:
        return None, "Season is required."

    season = db.session.get(Season, int(seasonID))
    if not season:
        return None, "Season not found."

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
        seasonID=int(seasonID),
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


def update_event(event_id: int, eventName: str, eventDate: str, eventTime: str, eventLocation: str, seasonID: int):
    ev = db.session.get(Event, event_id)
    if not ev:
        return None, "Event not found."

    if not eventName or not eventLocation:
        return None, "Event name and location are required."

    if not seasonID:
        return None, "Season is required."

    season = db.session.get(Season, int(seasonID))
    if not season:
        return None, "Season not found."

    try:
        ev.eventDate = datetime.strptime(eventDate, "%Y-%m-%d").date()
    except Exception:
        return None, "Invalid date. Use YYYY-MM-DD."

    try:
        ev.time = datetime.strptime(eventTime, "%H:%M").time()
    except Exception:
        return None, "Invalid time. Use HH:MM (24h)."

    ev.eventName = eventName.strip()
    ev.location  = eventLocation.strip()
    ev.seasonID  = int(seasonID)
    db.session.commit()
    return ev, None
from App.models import Event
from App.models import db

def get_json(eventID):
    event = db.session.get(Event, eventID)
    return{
        'eventID':event.eventName,
        'eventDate':event.eventDate,
        'time':event.time,
        'location':event.location
    }
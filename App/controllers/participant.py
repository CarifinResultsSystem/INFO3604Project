from sqlite3 import IntegrityError
from App.database import db
from App.models import Participant


# Create Participant
def create_participant(participantID, firstName, lastName, gender, dateOfBirth, location, institutionID):
    if not firstName or not lastName:
        raise ValueError("First name and last name are required")

    newParticipant = Participant(
        participantID=participantID,
        firstName=firstName.strip(),
        lastName=lastName.strip(),
        gender=gender,
        dateOfBirth=dateOfBirth,
        location=location,
        institutionID=institutionID
    )

    try:
        db.session.add(newParticipant)
        db.session.commit()
        return newParticipant
    except IntegrityError:
        db.session.rollback()
        raise ValueError("Participant already exists or invalid data")


# Read Participants
def get_participant(participantID):
    return db.session.get(Participant, participantID)

def get_all_participants():
    return db.session.scalars(db.select(Participant)).all()

def get_all_participants_json():
    participants = get_all_participants()
    if not participants:
        return []
    return [p.get_json() for p in participants]


# Update Participant
def update_participant(participantID, **kwargs):
    participant = get_participant(participantID)
    if not participant:
        return False

    for key, value in kwargs.items():
        if hasattr(participant, key) and value is not None:
            setattr(participant, key, value)

    try:
        db.session.commit()
        return True
    except IntegrityError:
        db.session.rollback()
        raise ValueError("Failed to update participant")


# Delete Participant
def delete_participant(participantID):
    participant = get_participant(participantID)
    if participant:
        db.session.delete(participant)
        db.session.commit()
        return True
    return False
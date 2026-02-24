from sqlite3 import IntegrityError
from App.database import db
from App.models import AutomatedResult


# Create Automated Result
def create_automated_result(score, participantID, eventID, pointsID):
    if score is None:
        raise ValueError("Score is required")

    result = AutomatedResult(
        score=score,
        participantID=participantID,
        eventID=eventID,
        pointsID=pointsID
    )

    try:
        db.session.add(result)
        db.session.commit()
        return result
    except IntegrityError:
        db.session.rollback()
        raise ValueError("Failed to create automated result")


# Read Automated Results
def get_automated_result(resultID):
    return db.session.get(AutomatedResult, resultID)


def get_all_automated_results():
    return db.session.scalars(db.select(AutomatedResult)).all()


def get_all_automated_results_json():
    results = get_all_automated_results()
    if not results:
        return []
    return [r.get_json() for r in results]


def get_results_by_participant(participantID):
    return AutomatedResult.query.filter_by(participantID=participantID).all()


def get_results_by_event(eventID):
    return AutomatedResult.query.filter_by(eventID=eventID).all()


# Update Automated Result
def update_automated_result(resultID, **kwargs):
    result = get_automated_result(resultID)
    if not result:
        return False

    for key, value in kwargs.items():
        if hasattr(result, key) and value is not None:
            setattr(result, key, value)

    try:
        db.session.commit()
        return True
    except IntegrityError:
        db.session.rollback()
        raise ValueError("Failed to update automated result")


# Confirm Result
def confirm_result(resultID):
    result = get_automated_result(resultID)
    if not result:
        return False

    result.confirmed = True
    db.session.commit()
    return True


# Delete Automated Result
def delete_automated_result(resultID):
    result = get_automated_result(resultID)
    if result:
        db.session.delete(result)
        db.session.commit()
        return True
    return False
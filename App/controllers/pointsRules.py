from sqlite3 import IntegrityError
from App.models import PointsRules
from App.database import db

# Create Points Rule
def create_points_rule(eventType, conditionType, conditionValue, upperLimit, lowerLimit, seasonID):

    if not eventType or not conditionType:
        raise ValueError("Event type and condition type are required")

    newRule = PointsRules(
        eventType=eventType.strip(),
        conditionType=conditionType.strip(),
        conditionValue=int(conditionValue),
        upperLimit=int(upperLimit),
        lowerLimit=int(lowerLimit),
        seasonID=int(seasonID)
    )

    try:
        db.session.add(newRule)
        db.session.commit()
        return newRule
    except IntegrityError:
        db.session.rollback()
        raise ValueError("Failed to create points rule")

# Read Points Rules
def get_points_rule(pointsID):
    return db.session.get(PointsRules, pointsID)

def get_points_rules_by_season(seasonID):
    result = db.session.execute(
        db.select(PointsRules).filter_by(seasonID=seasonID)
    )
    return result.scalars().all()

def get_all_points_rules():
    return db.session.scalars(db.select(PointsRules)).all()

def get_all_points_rules_json():
    rules = get_all_points_rules()
    if not rules:
        return []
    return [r.get_json() for r in rules]

# Update Points Rule
def update_points_rule(pointsID, **kwargs):
    rule = get_points_rule(pointsID)
    if not rule:
        return False

    for key, value in kwargs.items():
        if hasattr(rule, key) and value is not None:
            setattr(rule, key, value)

    try:
        db.session.commit()
        return True
    except IntegrityError:
        db.session.rollback()
        raise ValueError("Failed to update points rule")

# Delete Points Rule
def delete_points_rule(pointsID):
    rule = get_points_rule(pointsID)
    if rule:
        db.session.delete(rule)
        db.session.commit()
        return True
    return False
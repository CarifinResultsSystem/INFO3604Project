from App.models import PointsRules
from App.database import db


# Create Individual Points Rule
def create_individual_rule(eventID, seasonID, placement, label, points):
    """1st/2nd/3rd place award rule."""
    if not placement or not label:
        raise ValueError("Placement and label are required.")
    rule = PointsRules(
        eventID=int(eventID), seasonID=int(seasonID),
        ruleType="individual",
        placement=int(placement),
        label=label.strip(),
        points=float(points),
    )
    db.session.add(rule)
    db.session.commit()
    return rule


# Create Team Points Rule
def create_team_rule(eventID, seasonID, category, label, points):
    """One row = one awarded-for condition inside a category."""
    if not category or not label:
        raise ValueError("Category and label are required.")
    rule = PointsRules(
        eventID=int(eventID), seasonID=int(seasonID),
        ruleType="team",
        category=category.strip(),
        label=label.strip(),
        points=float(points),
    )
    db.session.add(rule)
    db.session.commit()
    return rule


# Read Points Rules
def get_points_rule(pointsID):
    return db.session.get(PointsRules, pointsID)


def get_rules_by_event(eventID):
    return PointsRules.query.filter_by(eventID=eventID).all()


def get_rules_by_season(seasonID):
    return PointsRules.query.filter_by(seasonID=seasonID).all()


def get_all_points_rules():
    return PointsRules.query.all()


def get_all_points_rules_json():
    return [r.get_json() for r in get_all_points_rules()]


# Update Points Rule
def update_points_rule(pointsID, **kwargs):
    rule = get_points_rule(pointsID)
    if not rule:
        return False
    allowed = {"placement", "category", "label", "points", "ruleType"}
    for key, value in kwargs.items():
        if key in allowed and value is not None:
            setattr(rule, key, value)
    db.session.commit()
    return True


# Delete Points Rule
def delete_points_rule(pointsID):
    rule = get_points_rule(pointsID)
    if not rule:
        return False
    db.session.delete(rule)
    db.session.commit()
    return True


def delete_rules_by_event(eventID):
    PointsRules.query.filter_by(eventID=eventID).delete()
    db.session.commit()
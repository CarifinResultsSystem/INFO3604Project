from sqlalchemy.exc import IntegrityError

from App.database import db
from App.models.challenge import Challenge
from App.models.pointsRules import PointsRules
from App.models import Event, Participant, Season


def create_challenge(challengeName, seasonID=None, description=None, bonusPoints=0.0, eventIDs=None):
    name = (challengeName or "").strip()
    if not name:
        return None, "Challenge name is required."

    if Challenge.query.filter(
        db.func.lower(Challenge.challengeName) == name.lower()
    ).first():
        return None, f'A challenge named "{name}" already exists.'

    if seasonID:
        season = db.session.get(Season, int(seasonID))
        if not season:
            return None, "Season not found."

    try:
        bp = float(bonusPoints or 0)
    except (ValueError, TypeError):
        bp = 0.0

    challenge = Challenge(
        challengeName=name,
        seasonID=int(seasonID) if seasonID else None,
        description=(description or "").strip() or None,
        bonusPoints=bp,
    )

    if eventIDs:
        for eid in eventIDs:
            ev = db.session.get(Event, int(eid))
            if ev:
                challenge.events.append(ev)

    db.session.add(challenge)
    try:
        db.session.commit()
        return challenge, None
    except IntegrityError:
        db.session.rollback()
        return None, "Could not create challenge (duplicate name?)."


def get_challenge(challengeID):
    return db.session.get(Challenge, int(challengeID))


def get_all_challenges():
    return Challenge.query.order_by(Challenge.challengeName.asc()).all()


def update_challenge(challengeID, challengeName=None, description=None,
                     bonusPoints=None, seasonID=None, eventIDs=None):
    challenge = db.session.get(Challenge, int(challengeID))
    if not challenge:
        return None, "Challenge not found."

    if challengeName is not None:
        name = challengeName.strip()
        if not name:
            return None, "Challenge name cannot be empty."
        duplicate = Challenge.query.filter(
            db.func.lower(Challenge.challengeName) == name.lower(),
            Challenge.challengeID != challenge.challengeID,
        ).first()
        if duplicate:
            return None, f'Another challenge named "{name}" already exists.'
        challenge.challengeName = name

    if description is not None:
        challenge.description = description.strip() or None

    if bonusPoints is not None:
        try:
            challenge.bonusPoints = float(bonusPoints)
        except (ValueError, TypeError):
            return None, "Invalid bonus points value."

    if seasonID is not None:
        season = db.session.get(Season, int(seasonID))
        if not season:
            return None, "Season not found."
        challenge.seasonID = int(seasonID)

    if eventIDs is not None:
        challenge.events.clear()
        for eid in eventIDs:
            ev = db.session.get(Event, int(eid))
            if ev:
                challenge.events.append(ev)

    try:
        db.session.commit()
        return challenge, None
    except IntegrityError:
        db.session.rollback()
        return None, "Could not update challenge."


def delete_challenge(challengeID):
    challenge = db.session.get(Challenge, int(challengeID))
    if not challenge:
        return False
    db.session.delete(challenge)
    try:
        db.session.commit()
        return True
    except Exception:
        db.session.rollback()
        return False


def attach_event(challengeID, eventID):
    challenge = db.session.get(Challenge, int(challengeID))
    event     = db.session.get(Event, int(eventID))
    if not challenge or not event:
        return False
    if event not in challenge.events:
        challenge.events.append(event)
    try:
        db.session.commit()
        return True
    except Exception:
        db.session.rollback()
        return False


def detach_event(challengeID, eventID):
    challenge = db.session.get(Challenge, int(challengeID))
    event     = db.session.get(Event, int(eventID))
    if not challenge or not event:
        return False
    if event in challenge.events:
        challenge.events.remove(event)
    try:
        db.session.commit()
        return True
    except Exception:
        db.session.rollback()
        return False


def get_challenge_rules(challengeID):
    rules = PointsRules.query.filter_by(challengeID=int(challengeID)).all()

    individual, team_map, team_order = [], {}, []
    for r in rules:
        if r.ruleType == "individual":
            individual.append({
                "pointsID":  r.pointsID,
                "placement": r.placement,
                "label":     r.label or "",
                "points":    float(r.points),
            })
        else:
            cat = r.category or "Uncategorised"
            if cat not in team_map:
                team_map[cat] = []
                team_order.append(cat)
            team_map[cat].append({
                "pointsID":      r.pointsID,
                "conditionType": cat,
                "label":         r.label or "",
                "points":        float(r.points),
            })

    individual.sort(key=lambda x: x["placement"] or 0)

    team = []
    for cat in team_order:
        team.extend(team_map[cat])

    return {"individual": individual, "team": team}


def save_challenge_rules(challengeID, payload):
    challenge = db.session.get(Challenge, int(challengeID))
    if not challenge:
        return False, "Challenge not found."

    try:
        for item in payload.get("individual", []):
            rid = item.get("pointsID")
            if rid:
                r = db.session.get(PointsRules, int(rid))
                if not r or r.challengeID != int(challengeID):
                    continue
                r.placement = int(item.get("placement", 0))
                r.label     = (item.get("label") or "").strip()
                r.points    = float(item.get("points") or 0)
            else:
                r = PointsRules(
                    seasonID    = challenge.seasonID,
                    ruleType    = "individual",
                    placement   = int(item.get("placement", 0)),
                    label       = (item.get("label") or "").strip(),
                    points      = float(item.get("points") or 0),
                    challengeID = int(challengeID),
                )
                db.session.add(r)

        for item in payload.get("team", []):
            rid = item.get("pointsID")
            if rid:
                r = db.session.get(PointsRules, int(rid))
                if not r or r.challengeID != int(challengeID):
                    continue
                r.category = (item.get("conditionType") or "").strip()
                r.label    = (item.get("label") or "").strip()
                r.points   = float(item.get("points") or 0)
            else:
                r = PointsRules(
                    seasonID    = challenge.seasonID,
                    ruleType    = "team",
                    category    = (item.get("conditionType") or "").strip(),
                    label       = (item.get("label") or "").strip(),
                    points      = float(item.get("points") or 0),
                    challengeID = int(challengeID),
                )
                db.session.add(r)

        db.session.commit()
        return True, None

    except Exception as e:
        db.session.rollback()
        return False, str(e)


def delete_challenge_rule(ruleID, challengeID):
    r = db.session.get(PointsRules, int(ruleID))
    if not r or r.challengeID != int(challengeID):
        return False
    db.session.delete(r)
    try:
        db.session.commit()
        return True
    except Exception:
        db.session.rollback()
        return False
from datetime import datetime
from sqlite3 import IntegrityError
from sqlalchemy import func, case

from App.database import db
from App.models.hr import HRReport
from App.models import AutomatedResult, User, Event, participant_events

def _current_season() -> str:
    return str(datetime.utcnow().year)

# DASHBOARD
def get_institutions_this_year():
    try:
        from App.models import Institution
        return db.session.query(Institution).count()
    except Exception as e:
        print(f"[HR] get_institutions_this_year error: {e}")
        return 0


def get_participants_this_year():
    try:
        from App.models import Participant
        return db.session.query(Participant).count()
    except Exception as e:
        print(f"[HR] get_participants_this_year error: {e}")
        return 0


def get_institutions_per_year():
    try:
        from App.models import Institution, Season
        from App.models.participant_event import participant_events
        from App.models import Event, Participant

        seasons = Season.get_all()
        result = {}
        for s in seasons:
            count = (
                db.session.query(Institution.institutionID)
                .join(Participant, Participant.institutionID == Institution.institutionID)
                .join(participant_events,
                      participant_events.c.participantID == Participant.participantID)
                .join(Event, Event.eventID == participant_events.c.eventID)
                .filter(Event.seasonID == s.seasonID)
                .distinct()
                .count()
            )
            if count > 0:
                result[str(s.year)] = count

        current = _current_season()
        if current not in result:
            from App.models import Institution
            result[current] = db.session.query(Institution).count()

        return result
    except Exception as e:
        print(f"[HR] get_institutions_per_year error: {e}")
        from App.models import Institution
        return {_current_season(): db.session.query(Institution).count()}

def get_reports_count(userID=None):
    q = db.session.query(HRReport)
    if userID:
        q = q.filter_by(generated_by=userID)
    return q.count()

def get_latest_report(userID=None):
    q = db.session.query(HRReport).order_by(HRReport.generated_at.desc())
    if userID:
        q = q.filter_by(generated_by=userID)
    return q.first()

# REPORT
def get_all_reports(userID=None):
    q = db.session.query(HRReport).order_by(HRReport.generated_at.desc())
    if userID:
        q = q.filter_by(generated_by=userID)
    return q.all()


def get_report(reportID):
    return db.session.get(HRReport, reportID)


def create_report(filename, generated_by, season=None, filepath=None, pdf_data=None):
    season = season or _current_season()
    report = HRReport(
        filename=filename,
        generated_by=generated_by,
        season=season,
        filepath=filepath,
        pdf_data=pdf_data,
    )
    try:
        db.session.add(report)
        db.session.commit()
        return report
    except IntegrityError:
        db.session.rollback()
        raise ValueError("Failed to create report record")


def mark_report_read(reportID):
    report = get_report(reportID)
    if not report:
        return False
    report.is_read = True
    db.session.commit()
    return True


def mark_all_reports_read(userID):
    db.session.query(HRReport).filter_by(generated_by=userID, is_read=False).update({"is_read": True})
    db.session.commit()
    return True


def delete_report(reportID):
    report = get_report(reportID)
    if report:
        db.session.delete(report)
        db.session.commit()
        return True
    return False


def delete_all_reports(userID):
    db.session.query(HRReport).filter_by(generated_by=userID).delete()
    db.session.commit()
    return True

def build_report_data(season=None):
    season = season or _current_season()

    institutions_count = get_institutions_this_year()
    participants_count = get_participants_this_year()
    reports_count      = get_reports_count()

    # Participants
    participants = []
    try:
        from App.models import Participant
        rows = Participant.query.all()
        for p in rows:
            participants.append({
                "firstName":   p.firstName,
                "lastName":    p.lastName,
                "gender":      p.gender,
                "dateOfBirth": p.dateOfBirth,
                "location":    p.location,
                "institution": p.institution.insName if p.institution else "—",
                "events":      [e.eventName for e in p.events] if p.events else [],
            })
    except Exception as e:
        print(f"[HR] participants error: {e}")

    awards = []
    try:
        from App.models import ScoreDocument, Season
        from App.views.judge import parse_hierarchical_document

        # Find season by year for filtering documents
        season_obj = None
        try:
            season_obj = db.session.query(Season).filter_by(year=int(season)).first()
        except (ValueError, TypeError):
            pass

        # Get all confirmed documents
        confirmed_docs = db.session.query(ScoreDocument).filter_by(confirmed=True).all()
        if season_obj and season_obj.seasonID:
            confirmed_docs = [d for d in confirmed_docs if d.seasonID == season_obj.seasonID]

        if confirmed_docs:
            # Merge all confirmed documents — accumulate scores per institution per challenge/event
            institution_totals = {}   # inst -> total points
            event_scores = {}         # event_name -> {inst -> points}

            for doc in confirmed_docs:
                try:
                    parsed = parse_hierarchical_document(doc)
                    if not parsed:
                        continue

                    # Overall totals
                    for inst, pts in parsed["calculated_totals"].items():
                        institution_totals[inst] = institution_totals.get(inst, 0.0) + pts

                    # Per-challenge/event scores
                    for challenge in parsed["challenges"]:
                        for event in challenge["events"]:
                            event_name = event["name"] or challenge["name"]
                            if not event_name:
                                continue
                            if event_name not in event_scores:
                                event_scores[event_name] = {}

                            if event["rules"]:
                                for rule in event["rules"]:
                                    for inst, v in rule["scores"].items():
                                        event_scores[event_name][inst] = \
                                            event_scores[event_name].get(inst, 0.0) + v
                            elif event.get("event_scores"):
                                for inst, v in event["event_scores"].items():
                                    event_scores[event_name][inst] = \
                                        event_scores[event_name].get(inst, 0.0) + v
                except Exception as e:
                    print(f"[HR] Error parsing document {doc.documentID}: {e}")
                    continue

            # Build overall winners list
            sorted_insts = sorted(institution_totals.items(), key=lambda x: x[1], reverse=True)
            for i, (inst, pts) in enumerate(sorted_insts, 1):
                awards.append({
                    "event_name":  "Overall",
                    "institution": inst,
                    "participant": None,
                    "place":       i,
                    "score":       round(pts, 2),
                })

            # Add event/challenge winners
            for event_name, scores in event_scores.items():
                if not scores:
                    continue
                sorted_event = sorted(scores.items(), key=lambda x: x[1], reverse=True)
                for i, (inst, pts) in enumerate(sorted_event, 1):
                    awards.append({
                        "event_name":  event_name,
                        "institution": inst,
                        "participant": None,
                        "place":       i,
                        "score":       round(pts, 2),
                    })
    except Exception as e:
        print(f"[HR] build_report_data awards error: {e}")
        pass

    error_summary = []
    try:
        rows = (
            db.session.query(
                AutomatedResult.errorType,
                func.count(AutomatedResult.resultID).label('total'),
                func.sum(
                    case((AutomatedResult.confirmed == True, 1), else_=0)
                ).label('resolved'),
            )
            .filter(AutomatedResult.errorType != None)
            .group_by(AutomatedResult.errorType)
            .order_by(func.count(AutomatedResult.resultID).desc())
            .all()
        )
        error_summary = [
            {
                "type":     row.errorType or "Unknown",
                "count":    row.total,
                "resolved": row.resolved,
                "open":     row.total - row.resolved,
            }
            for row in rows
        ]
    except Exception:
        pass

    return {
        "season":             season,
        "institutions_count": institutions_count,
        "participants_count": participants_count,
        "reports_count":      reports_count,
        "awards":             awards,
        "error_summary":      error_summary,
        "participants":       participants,
    }
from datetime import datetime
from sqlite3 import IntegrityError

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
        from App.models import Award
        award_rows = Award.query.filter_by(season=season).order_by(Award.place).all()
        for a in award_rows:
            awards.append({
                "event_name":  a.event_name if hasattr(a, 'event_name') else None,
                "institution": a.institution_name if hasattr(a, 'institution_name') else None,
                "participant": a.participant_name if hasattr(a, 'participant_name') else None,
                "place":       a.place if hasattr(a, 'place') else None,
                "score":       a.score if hasattr(a, 'score') else None,
            })
    except Exception:
        pass

    error_summary = []
    try:
        rows = (
            db.session.query(
                AutomatedResult.errorType,
                db.func.count(AutomatedResult.resultID).label('cnt')
            )
            .filter(
                AutomatedResult.errorType.isnot(None),
                db.extract('year', AutomatedResult.createdAt) == int(season)
            )
            .group_by(AutomatedResult.errorType)
            .order_by(db.desc('cnt'))
            .all()
        )
        error_summary = [{"type": r.errorType, "count": r.cnt} for r in rows]
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
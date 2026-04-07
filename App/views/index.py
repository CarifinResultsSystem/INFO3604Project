from flask import Blueprint, render_template, jsonify
from App.controllers import create_user, initialize
from App.models import Event, Season, Participant, Institution
from App.database import db
from datetime import date, datetime, timedelta

index_views = Blueprint('index_views', __name__)

@index_views.route('/', methods=['GET'])
def index_page():
    try:
        now = datetime.now()
        today = now.date()
        current_time = now.time()

        # Happening Now
        two_hours_ago = (now - timedelta(hours=2)).time()
        happening_now = Event.query.filter(
            Event.eventDate == today,
            Event.time <= current_time,
            Event.time >= two_hours_ago
        ).order_by(Event.time.desc()).first()

        # Up Next
        up_next = Event.query.filter(
            Event.eventDate == today,
            Event.time > current_time
        ).order_by(Event.time.asc()).limit(3).all()

        # Latest season stats
        latest_season = db.session.execute(
            db.select(Season).order_by(Season.year.desc())
        ).scalars().first()

        season_institution_count = 0
        season_participant_count = 0

        if latest_season:
            # Participants registered for any event in the latest season
            season_participants = db.session.execute(
                db.select(Participant)
                .join(Participant.events)
                .join(Event.season)
                .where(Season.seasonID == latest_season.seasonID)
                .distinct()
            ).scalars().all()

            season_participant_count = len(season_participants)

            # Institutions with at least one participant in the latest season
            institution_ids = {p.institutionID for p in season_participants if p.institutionID}
            season_institution_count = len(institution_ids)

        return render_template(
            'user/index.html',
            happening_now=happening_now,
            up_next=up_next,
            latest_season=latest_season,
            season_institution_count=season_institution_count,
            season_participant_count=season_participant_count,
        )
    except Exception as e:
        db.session.rollback()
        print(f"DEBUG: {e}")
        raise e

@index_views.route('/init', methods=['GET'])
def init():
    initialize()
    return jsonify(message='db initialized!')

@index_views.route('/health', methods=['GET'])
def health_check():
    return jsonify({'status': 'healthy'})
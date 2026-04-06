from flask import Blueprint, redirect, render_template, request, send_from_directory, jsonify
from App.controllers import create_user, initialize
from App.models import Event
from datetime import date, datetime, timedelta

index_views = Blueprint('index_views', __name__)

@index_views.route('/', methods=['GET'])
def index_page():
    now = datetime.now()
    today = now.date()
    current_time = now.time()

    # "Happening Now": events today whose start time is within the last 2 hours
    two_hours_ago = (now - timedelta(hours=2)).time()
    happening_now = Event.query.filter(
        Event.eventDate == today,
        Event.time <= current_time,
        Event.time >= two_hours_ago
    ).order_by(Event.time.desc()).first()

    # "Up Next": future events today, ordered by time
    up_next = Event.query.filter(
        Event.eventDate == today,
        Event.time > current_time
    ).order_by(Event.time.asc()).limit(3).all()

    return render_template(
        'user/index.html',
        happening_now=happening_now,
        up_next=up_next,
        now=now
    )

@index_views.route('/init', methods=['GET'])
def init():
    initialize()
    return jsonify(message='db initialized!')

@index_views.route('/health', methods=['GET'])
def health_check():
    return jsonify({'status': 'healthy'})
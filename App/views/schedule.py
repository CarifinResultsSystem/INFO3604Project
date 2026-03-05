from flask import Blueprint, render_template, jsonify, request, flash, redirect, url_for
from flask_jwt_extended import jwt_required, current_user as jwt_current_user

from datetime import date
from App.database import db
from App.models import Event, Season

schedule_views = Blueprint('schedule_views', __name__, template_folder='../templates')


'''
Page/Action Routes
'''

@schedule_views.route('/schedule', methods=['GET'])
def get_schedule_page():
    events  = db.session.execute(db.select(Event).order_by(Event.eventDate.asc())).scalars().all()
    seasons = db.session.execute(db.select(Season).order_by(Season.year.desc())).scalars().all()
    return render_template('user/schedule.html',
        events=events,
        seasons=seasons,
        today=date.today()
    )


'''
API Routes
'''

@schedule_views.route('/api/schedule', methods=['GET'])
def get_schedule_api():
    return jsonify([])
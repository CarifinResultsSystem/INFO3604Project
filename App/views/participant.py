from flask import Blueprint, render_template, jsonify, request
from flask_jwt_extended import jwt_required, current_user as jwt_current_user

from App.models import Participant, Event

participant_views = Blueprint('participant_views', __name__, template_folder='../templates')


'''
Page/Action Routes
'''

@participant_views.route('/participants', methods=['GET'])
def get_participants_page():
    participants = Participant.query.order_by(
        Participant.lastName.asc(),
        Participant.firstName.asc()
    ).all()
    events = Event.query.order_by(Event.eventName.asc()).all()

    return render_template(
        'user/participant.html',
        participants=participants,
        events=events,
    )


'''
API Routes
'''

@participant_views.route('/api/participants', methods=['GET'])
def get_participants_api():
    participants = Participant.query.order_by(
        Participant.lastName.asc(),
        Participant.firstName.asc()
    ).all()

    return jsonify([
        {
            "participantID": p.participantID,
            "firstName": p.firstName,
            "lastName": p.lastName,
            "location": p.location,
            "institution": p.institution.insName if p.institution else None,
            "events": [e.eventName for e in p.events],
        }
        for p in participants
    ])
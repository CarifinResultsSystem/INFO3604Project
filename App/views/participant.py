from flask import Blueprint, render_template, jsonify, request
from flask_jwt_extended import jwt_required, current_user as jwt_current_user

participant_views = Blueprint('participant_views', __name__, template_folder='../templates')


'''
Page/Action Routes
'''

@participant_views.route('/participants', methods=['GET'])
def get_participants_page():
    return render_template('user/participant.html')


'''
API Routes
'''

@participant_views.route('/api/participants', methods=['GET'])
def get_participants_api():
    return jsonify([])
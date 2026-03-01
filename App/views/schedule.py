from flask import Blueprint, render_template, jsonify, request, flash, redirect, url_for
from flask_jwt_extended import jwt_required, current_user as jwt_current_user

schedule_views = Blueprint('schedule_views', __name__, template_folder='../templates')


'''
Page/Action Routes
'''

@schedule_views.route('/schedule', methods=['GET'])
def get_schedule_page():
    return render_template('schedule.html')


'''
API Routes
'''

@schedule_views.route('/api/schedule', methods=['GET'])
def get_schedule_api():
    # Placeholder — replace with schedule-specific controller calls
    return jsonify([])
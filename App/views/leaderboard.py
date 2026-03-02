from flask import Blueprint, render_template, jsonify, request, flash, redirect, url_for
from flask_jwt_extended import jwt_required, current_user as jwt_current_user

from App.controllers import (
    get_all_users_json
)

leaderboard_views = Blueprint('leaderboard_views', __name__, template_folder='../templates')

'''
Page/Action Routes
'''

@leaderboard_views.route('/leaderboard', methods=['GET'])
def get_leaderboard_page():
    return render_template('leaderboard.html')


'''
API Routes
'''

@leaderboard_views.route('/api/leaderboard', methods=['GET'])
def get_leaderboard_api():
    return jsonify([])
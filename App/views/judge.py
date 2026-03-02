from flask import Blueprint, render_template
from flask_jwt_extended import jwt_required, current_user

judge_views = Blueprint('judge_views', __name__, template_folder='../templates')

@judge_views.route('/judge/')
@jwt_required()
def judge_dashboard():
    return render_template('judge/judge.html', user=current_user)
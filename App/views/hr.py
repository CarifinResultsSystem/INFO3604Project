from flask import Blueprint, render_template
from flask_jwt_extended import jwt_required, current_user

hr_views = Blueprint('hr_views', __name__, template_folder='../templates')

@hr_views.route('/hr/')
@jwt_required()
def hr_dashboard():
    return render_template('hr/hr.html', user=current_user)
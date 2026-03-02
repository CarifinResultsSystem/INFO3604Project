from flask import Blueprint, render_template, jsonify, request, flash, redirect, url_for
from flask_jwt_extended import jwt_required, current_user, unset_jwt_cookies, set_access_cookies

from App.controllers import login

auth_views = Blueprint('auth_views', __name__, template_folder='../templates')


'''
Page/Action Routes
'''

@auth_views.route('/login', methods=['GET'])
def login_page():
    return render_template('login.html')


@auth_views.route('/login', methods=['POST'])
def login_action():
    data = request.form
    token = login(data['username'], data['password'])
    if not token:
        flash('Bad username or password given', 'error')
        return redirect(url_for('auth_views.login_page'))

    # Retrieve the user by username
    from App.database import db
    from App.models import User

    user = db.session.execute(db.select(User).filter_by(username=data.get('username'))).scalar_one_or_none()
    if not user:
        flash('User not found', 'error')
        return redirect(url_for('auth_views.login_page'))

    # Determine redirect URL based on role
    if user.role == "admin":
        redirect_url = url_for('admin_views.admin_dashboard')
    elif user.role == "scoretaker":
        redirect_url = url_for('scoretaker_views.scoretaker_dashboard')
    elif user.role == "judge":
        redirect_url = url_for('judge_views.judge_dashboard')
    elif user.role == "hr":
        redirect_url = url_for('hr_views.hr_dashboard')
    else:
        redirect_url = url_for('index_views.index_page')

    response = redirect(redirect_url)
    flash('Login Successful', 'success')
    set_access_cookies(response, token)
    return response

@auth_views.route('/logout', methods=['GET'])
def logout_action():
    response = redirect(url_for('index_views.index_page'))
    flash('Logged Out!', 'success')
    unset_jwt_cookies(response)
    return response

@auth_views.route('/logout_to_public', methods=['GET'])
def logout_to_public():
    """Logs the user out and redirects to the public dashboard"""
    from flask import redirect, flash, url_for
    from flask_jwt_extended import unset_jwt_cookies

    response = redirect(url_for('index_views.index_page'))  # public dashboard
    flash("You have been logged out to access the Public Viewer Dashboard", "success")
    unset_jwt_cookies(response)
    return response


@auth_views.route('/identify', methods=['GET'])
@jwt_required()
def identify_page():
    return render_template('message.html', title="Identify", message=f"You are logged in as {current_user.userID} - {current_user.username}")


'''
API Routes
'''

@auth_views.route('/api/login', methods=['POST'])
def user_login_api():
    data = request.json
    token = login(data['username'], data['password'])
    if not token:
        return jsonify(message='bad username or password given'), 401
    response = jsonify(access_token=token)
    set_access_cookies(response, token)
    return response


@auth_views.route('/api/identify', methods=['GET'])
@jwt_required()
def identify_user():
    return jsonify({'message': f"username: {current_user.username}, id : {current_user.userID}"})


@auth_views.route('/api/logout', methods=['GET'])
def logout_api():
    response = jsonify(message="Logged Out!")
    unset_jwt_cookies(response)
    return response
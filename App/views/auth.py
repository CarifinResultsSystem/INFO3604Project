from flask import Blueprint, render_template, jsonify, request, flash, redirect, url_for
from flask_jwt_extended import jwt_required, current_user, unset_jwt_cookies, set_access_cookies

from App.controllers import login
from App.controllers.user import create_user
from App.database import db
from App.models import User

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

    user = db.session.execute(
        db.select(User).filter_by(username=data.get('username'))
    ).scalar_one_or_none()

    if not user:
        flash('User not found', 'error')
        return redirect(url_for('auth_views.login_page'))

    # Redirect based on role
    role_routes = {
        "admin":      'admin_views.admin_dashboard',
        "scoretaker": 'scoretaker_views.scoretaker_dashboard',
        "judge":      'judge_views.judge_dashboard',
        "hr":         'hr_views.hr_dashboard',
    }
    redirect_url = url_for(role_routes.get(user.role, 'index_views.index_page'))

    response = redirect(redirect_url)
    flash('Login Successful', 'success')
    set_access_cookies(response, token)
    return response


@auth_views.route('/register', methods=['POST'])
def register_action():
    username         = request.form.get('username', '').strip()
    email            = request.form.get('email', '').strip()
    password         = request.form.get('password', '')
    confirm_password = request.form.get('confirm_password', '')

    if not username or not email or not password:
        flash('All fields are required.', 'error')
        return redirect(url_for('auth_views.login_page'))

    if password != confirm_password:
        flash('Passwords do not match.', 'error')
        return redirect(url_for('auth_views.login_page'))

    if len(password) < 6:
        flash('Password must be at least 6 characters.', 'error')
        return redirect(url_for('auth_views.login_page'))

    existing_username = db.session.execute(
        db.select(User).filter_by(username=username)
    ).scalar_one_or_none()

    if existing_username:
        flash('That username is already taken.', 'error')
        return redirect(url_for('auth_views.login_page'))

    existing_email = db.session.execute(
        db.select(User).filter_by(email=email)
    ).scalar_one_or_none()

    if existing_email:
        flash('An account with that email already exists.', 'error')
        return redirect(url_for('auth_views.login_page'))

    try:
        create_user(username=username, role='user', email=email, password=password)
    except ValueError as e:
        flash(str(e), 'error')
        return redirect(url_for('auth_views.login_page'))
    except Exception:
        flash('An unexpected error occurred. Please try again.', 'error')
        return redirect(url_for('auth_views.login_page'))

    token = login(username, password)
    if not token:
        # Account created but auto-login failed — send to login page
        flash('Account created! Please sign in.', 'success')
        return redirect(url_for('auth_views.login_page'))

    flash('Account created successfully. Welcome!', 'success')
    response = redirect(url_for('index_views.index_page'))
    set_access_cookies(response, token)
    return response


@auth_views.route('/logout', methods=['GET'])
def logout_action():
    response = redirect(url_for('index_views.index_page'))
    flash('Logged Out!', 'success')
    unset_jwt_cookies(response)
    return response


@auth_views.route('/identify', methods=['GET'])
@jwt_required()
def identify_page():
    return render_template(
        'message.html',
        title="Identify",
        message=f"You are logged in as {current_user.userID} - {current_user.username}"
    )


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
    return jsonify({
        'message': f"username: {current_user.username}, id: {current_user.userID}"
    })


@auth_views.route('/api/logout', methods=['GET'])
def logout_api():
    response = jsonify(message="Logged Out!")
    unset_jwt_cookies(response)
    return response
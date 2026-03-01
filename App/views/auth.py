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
    response = redirect(url_for('index_views.index_page'))
    flash('Login Successful', 'success')
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
    return render_template('message.html', title="Identify", message=f"You are logged in as {current_user.id} - {current_user.username}")


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
    return jsonify({'message': f"username: {current_user.username}, id : {current_user.id}"})


@auth_views.route('/api/logout', methods=['GET'])
def logout_api():
    response = jsonify(message="Logged Out!")
    unset_jwt_cookies(response)
    return response
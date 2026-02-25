from flask import Flask
from flask_cors import CORS
from flask_sqlalchemy import SQLAlchemy
from flask.cli import with_appcontext
import click

from .views import views, setup_admin
from .config import load_config
from .database import *
from .controllers import setup_jwt
from .controllers.user import *

db = SQLAlchemy()

def add_views(app):
    for view in views:
        app.register_blueprint(view)

def create_app(overrides={}):
    app = Flask(__name__)
    load_config(app, overrides)
    CORS(app)
    add_views(app)
    init_db(app)
    jwt = setup_jwt(app)
    setup_admin(app)

    @jwt.invalid_token_loader
    @jwt.unauthorized_loader
    def custom_unauthorized_responce(error):
        return #render_template('401.html', error=error), 401 <= To be modified when templates are made
    
#------------------------ USER CLI TESTS -------------------------
    
    # Create User (flask create-user <username> <role> <email> <password>)
    @app.cli.command("create-user")
    @click.argument("username")
    @click.argument("role")
    @click.argument("email")
    @click.argument("password")
    @with_appcontext
    def create_user_command(username, role, email, password):
        try:
            user = create_user(username, role, email, password)
            click.echo(f"User created successfully: {user}")
        except ValueError as e:
            click.echo(f"Error: {e}")

    # Get User by ID (flask get-user <user_id>)
    @app.cli.command("get-user")
    @click.argument("user_id", type=int)
    @with_appcontext
    def get_user_command(user_id):
        user = get_user(user_id)
        if user:
            click.echo(f"User found: {user.get_json()}")
        else:
            click.echo(f"No user found with ID {user_id}")

    # Get User by Username (flask get-user-by-username <username>)
    @app.cli.command("get-user-by-username")
    @click.argument("username")
    @with_appcontext
    def get_user_by_username_command(username):
        user = get_user_by_username(username)
        if user:
            click.echo(f"User found: {user.get_json()}")
        else:
            click.echo(f"No user found with username '{username}'")

    # Get All Users (returns list of user jsons)
    @app.cli.command("get-all-users")
    @with_appcontext
    def get_all_users_command():
        users = get_all_users()
        if users:
            for user in users:
                click.echo(user.get_json())
        else:
            click.echo("No users found.")


#------------------------ ADMIN CLI TESTS ------------------------
#------------------------ JUDGE CLI TESTS ------------------------
#---------------------- SCORETAKER CLI TESTS ---------------------
#------------------------ EVENT CLI TESTS ------------------------
#------------------------ SEASON CLI TESTS -----------------------
#--------------------- INSTITUTION CLI TESTS ---------------------
#--------------------- PARTICIPANT CLI TESTS ---------------------
#--------------------- LEADERBOARD CLI TESTS ---------------------
#--------------------- POINTS RULES CLI TESTS --------------------
#------------------ AUTOMATED RESULTS CLI TESTS ------------------
    
    app.app_context().push()
    return app
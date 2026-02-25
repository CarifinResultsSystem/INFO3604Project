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

    # Update Username (flask update-username <user_id> <new_username>)
    @app.cli.command("update-username")
    @click.argument("user_id", type=int)
    @click.argument("new_username")
    @with_appcontext
    def update_username_command(user_id, new_username):
        try:
            result = update_user_username(user_id, new_username)
            if result:
                click.echo(f"Username updated successfully.")
            else:
                click.echo(f"No user found with ID {user_id}")
        except ValueError as e:
            click.echo(f"Error: {e}")

    # Update Email (flask update-email <user_id> <new_email>)
    @app.cli.command("update-email")
    @click.argument("user_id", type=int)
    @click.argument("new_email")
    @with_appcontext
    def update_email_command(user_id, new_email):
        try:
            result = update_user_email(user_id, new_email)
            if result:
                click.echo(f"Email updated successfully.")
            else:
                click.echo(f"No user found with ID {user_id}")
        except ValueError as e:
            click.echo(f"Error: {e}")

    # Update Password (flask update-password <user_id> <new_password>)
    @app.cli.command("update-password")
    @click.argument("user_id", type=int)
    @click.argument("new_password")
    @with_appcontext
    def update_password_command(user_id, new_password):
        try:
            result = update_user_password(user_id, new_password)
            if result:
                click.echo(f"Password updated successfully.")
            else:
                click.echo(f"No user found with ID {user_id}")
        except ValueError as e:
            click.echo(f"Error: {e}")

    # Update Role (flask update-role <user_id> <new_role>)
    @app.cli.command("update-role")
    @click.argument("user_id", type=int)
    @click.argument("new_role")
    @with_appcontext
    def update_role_command(user_id, new_role):
        try:
            result = update_user_role(user_id, new_role)
            if result:
                click.echo(f"Role updated successfully.")
            else:
                click.echo(f"No user found with ID {user_id}")
        except ValueError as e:
            click.echo(f"Error: {e}")

    # Delete User (flask delete-user <user_id>)
    @app.cli.command("delete-user")
    @click.argument("user_id", type=int)
    @with_appcontext
    def delete_user_command(user_id):
        result = delete_user(user_id)
        if result:
            click.echo(f"User {user_id} deleted successfully.")
        else:
            click.echo(f"No user found with ID {user_id}")

    # Authenticate User (flask authenticate-user <username> <password>)
    @app.cli.command("authenticate-user")
    @click.argument("username")
    @click.argument("password")
    @with_appcontext
    def authenticate_user_command(username, password):
        user = authenticate_user(username, password)
        if user:
            click.echo(f"Authentication successful: {user.get_json()}")
        else:
            click.echo(f"Authentication failed: invalid username or password.")

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
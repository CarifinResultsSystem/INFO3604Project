from flask import Flask
from flask_cors import CORS
from flask_sqlalchemy import SQLAlchemy
from flask.cli import with_appcontext
import click


from App.controllers.user import *
from App.controllers.judge import *
from App.controllers.admin import *
from App.controllers.institution import *
from App.controllers.leaderboard import *
from App.controllers.participant import *
from App.controllers.automatedResult import *

from .views import views, setup_admin
from .config import load_config
from .database import *
from .controllers import setup_jwt


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

    #Assign Role (flask assign-role <user_id> <role>)
    @app.cli.command("assign-role")
    @click.argument("user_id", type=int)
    @click.argument("role", type=str)
    @with_appcontext
    def assign_role_command(user_id, role):
        user = get_user(user_id)
        role = assignRole(user_id, role)
        if role:
            click.echo(f"User {user} was assigned as {role} successfully")
        else:
            click.echo(f"User {user} assignment failed")
            
#------------------------ JUDGE CLI TESTS ------------------------
    
    # Get Judge Profile (flask get-judge <user_id>)
    @app.cli.command("get-judge")
    @click.argument("user_id", type=int)
    @with_appcontext
    def get_judge_command(user_id):
        judge = get_judge(user_id)
        if judge:
            click.echo(f"Judge found: {judge.get_json()}")
        else:
            click.echo(f"No judge found with userID {user_id}")

    # Edit Automated Result (flask edit-result <judge_id> <result_id> field=value ...)
    @app.cli.command("edit-result")
    @click.argument("judge_id", type=int)
    @click.argument("result_id", type=int)
    @click.argument("updates", nargs=-1)
    @with_appcontext
    def edit_result_command(judge_id, result_id, updates):
        try:
            update_dict = {}
            for item in updates:
                key, value = item.split("=")
                update_dict[key] = value

            result = edit_results(judge_id, result_id, **update_dict)
            click.echo(f"Result updated successfully: {result.get_json()}")

        except ValueError as e:
            click.echo(f"Error: {e}")
        except Exception:
            click.echo("Invalid update format. Use field=value")

    # Confirm Score (flask confirm-score <judge_id> <result_id>)
    @app.cli.command("confirm-score")
    @click.argument("judge_id", type=int)
    @click.argument("result_id", type=int)
    @with_appcontext
    def confirm_score_command(judge_id, result_id):
        try:
            confirm_score(judge_id, result_id)
            click.echo("Score confirmed successfully.")
        except ValueError as e:
            click.echo(f"Error: {e}")

    # Get Automated Result by ID (flask get-result <result_id>)
    @app.cli.command("get-result")
    @click.argument("result_id", type=int)
    @with_appcontext
    def get_result_command(result_id):
        result = get_automated_result(result_id)
        if result:
            click.echo(result.get_json())
        else:
            click.echo(f"No automated result found with ID {result_id}")

    # Get All Automated Results (flask get-all-results)
    @app.cli.command("get-all-results")
    @with_appcontext
    def get_all_results_command():
        results = get_all_automated_results_json()
        if results:
            for r in results:
                click.echo(r)
        else:
            click.echo("No automated results found.")


#---------------------- SCORETAKER CLI TESTS ---------------------
#------------------------ EVENT CLI TESTS ------------------------

    # Create Event (flask create-event <event_name> <event_date> <event_time> <event_location>)
    @app.cli.command("create-event")
    @click.argument("event_name", type=str)
    @click.argument("event_date", type=click.DateTime())
    @click.argument("event_time", type=click.DateTime())
    @click.argument("event_location", type=str)
    @with_appcontext
    def create_event_command(event_name, event_date, event_time, event_location):
        try:
            event = createEvent(event_name, event_date, event_time, event_location)
            click.echo(f"Event created successfully: {event}")
        except ValueError as e:
            click.echo(f"Error: {e}")
        
#------------------------ SEASON CLI TESTS -----------------------
#--------------------- INSTITUTION CLI TESTS ---------------------

    # Create Institution (flask create-institution <ins_name>)
    @app.cli.command("create-institution")
    @click.argument("ins_name", type = str)
    @with_appcontext
    def get_institution_command(ins_name):
        try:
            institution = create_institution(ins_name)
            click.echo(f"Institution created successfully: {institution}")
        except ValueError as e:
            click.echo(f"Error: {e}")

    # Get Institution by ID (flask get-institution <ins_id>)
    @app.cli.command("get-institution")
    @click.argument("ins_id", type=int)
    @with_appcontext
    def get_institution_id_command(ins_id):
        institution = get_institution(ins_id)
        if institution:
            click.echo(f"Institution found: {institution.get_json()}")
        else:
            click.echo(f"No institution found with ID {ins_id}")
            
    # Get Institution by name (flask get-institution-name <ins_name>)
    @app.cli.command("get-institution-name")
    @click.argument("ins_name", type=str)
    @with_appcontext
    def get_institution_name_command(ins_name):
        institution = get_institution_by_name(ins_name)
        if institution:
            click.echo(f"Institution found: {institution.get_json()}")
        else:
            click.echo(f"No institution found with name {ins_name}")
            
    # Get All Institutions (flask get-all-institutions)
    @app.cli.command("get-all-institutions")
    @with_appcontext
    def get_all_institutions_command():
        institutions = get_all_institutions
        if institutions:
            for institution in institutions:
                click.echo(institution.get_json())
        else:
            click.echo("No institutions found.")

#--------------------- PARTICIPANT CLI TESTS ---------------------

    # Create Participant (flask create-participant <id> <firstName> <lastName> <gender> <dob> <location> <institutionID>)
    @app.cli.command("create-participant")
    @click.argument("participantID", type=int)
    @click.argument("firstName")
    @click.argument("lastName")
    @click.argument("gender")
    @click.argument("dateOfBirth")  # e.g., 'YYYY-MM-DD'
    @click.argument("location")
    @click.argument("institutionID", type=int)
    @with_appcontext
    def create_participant_command(participantID, firstName, lastName, gender, dateOfBirth, location, institutionID):
        try:
            participant = create_participant(participantID, firstName, lastName, gender, dateOfBirth, location, institutionID)
            click.echo(f"Participant created successfully: {participant.get_json()}")
        except ValueError as e:
            click.echo(f"Error: {e}")


    # Get Participant by ID (flask get-participant <participantID>)
    @app.cli.command("get-participant")
    @click.argument("participantID", type=int)
    @with_appcontext
    def get_participant_command(participantID):
        participant = get_participant(participantID)
        if participant:
            click.echo(f"Participant found: {participant.get_json()}")
        else:
            click.echo(f"No participant found with ID {participantID}")


    # Get All Participants (flask get-all-participants)
    @app.cli.command("get-all-participants")
    @with_appcontext
    def get_all_participants_command():
        participants = get_all_participants()
        if participants:
            for p in participants:
                click.echo(p.get_json())
        else:
            click.echo("No participants found.")


    # Update Participant (flask update-participant <participantID> --firstName=... --lastName=... etc.)
    @app.cli.command("update-participant")
    @click.argument("participantID", type=int)
    @click.option("--firstName", default=None)
    @click.option("--lastName", default=None)
    @click.option("--gender", default=None)
    @click.option("--dateOfBirth", default=None)
    @click.option("--location", default=None)
    @click.option("--institutionID", type=int, default=None)
    @with_appcontext
    def update_participant_command(participantID, firstName, lastName, gender, dateOfBirth, location, institutionID):
        kwargs = {
            "firstName": firstName,
            "lastName": lastName,
            "gender": gender,
            "dateOfBirth": dateOfBirth,
            "location": location,
            "institutionID": institutionID
        }
        # Remove None values
        kwargs = {k: v for k, v in kwargs.items() if v is not None}
        try:
            updated = update_participant(participantID, **kwargs)
            if updated:
                click.echo(f"Participant {participantID} updated successfully.")
            else:
                click.echo(f"No participant found with ID {participantID}")
        except ValueError as e:
            click.echo(f"Error: {e}")


    # Delete Participant (flask delete-participant <participantID>)
    @app.cli.command("delete-participant")
    @click.argument("participantID", type=int)
    @with_appcontext
    def delete_participant_command(participantID):
        deleted = delete_participant(participantID)
        if deleted:
            click.echo(f"Participant {participantID} deleted successfully.")
        else:
            click.echo(f"No participant found with ID {participantID}")


#--------------------- LEADERBOARD CLI TESTS ---------------------

    # Create Leaderboard (flask create-leaderboard <year>)
    @app.cli.command("create-leaderboard")
    @click.argument("year", type = int)
    @with_appcontext
    def create_leaderboard_command(year):
        try:
            leaderboard = create_leaderboard(year)
            click.echo(f"Leaderboard created successfully: {leaderboard}")
        except ValueError as e:
            click.echo(f"Error: {e}")
            
    # Get Leaderboard (flask get-leaderboard <year>)
    @app.cli.command("get-leaderboard")
    @click.argument("year", type=int)
    @with_appcontext
    def get_leaderboard_command(year):
        leaderboard = get_leaderboard(year)
        if leaderboard:
            click.echo(f"Leaderboard found: {leaderboard.get_json()}")
        else:
            click.echo(f"No leaderboard found for the year {year}")

#--------------------- POINTS RULES CLI TESTS --------------------


#------------------ AUTOMATED RESULTS CLI TESTS ------------------

# Create Automated Result (flask create-result <score> <participant_id> <event_id> <points_id>)
    @app.cli.command("create-result")
    @click.argument("score", type=float)
    @click.argument("participant_id", type=int)
    @click.argument("event_id", type=int)
    @click.argument("points_id", type=int)
    @with_appcontext
    def create_result_command(score, participant_id, event_id, points_id):
        try:
            result = create_automated_result(score, participant_id, event_id, points_id)
            click.echo(f"Automated result created: {result.get_json()}")
        except ValueError as e:
            click.echo(f"Error: {e}")

    # Get Automated Result by ID (flask get-result <result_id>)
    @app.cli.command("get-result")
    @click.argument("result_id", type=int)
    @with_appcontext
    def get_result_command(result_id):
        result = get_automated_result(result_id)
        if result:
            click.echo(result.get_json())
        else:
            click.echo(f"No automated result found with ID {result_id}")

    # Get All Automated Results (flask get-all-results)
    @app.cli.command("get-all-results")
    @with_appcontext
    def get_all_results_command():
        results = get_all_automated_results_json()
        if results:
            for r in results:
                click.echo(r)
        else:
            click.echo("No automated results found.")

    # Update Automated Result (flask update-result <result_id> field=value ...)
    @app.cli.command("update-result")
    @click.argument("result_id", type=int)
    @click.argument("updates", nargs=-1)
    @with_appcontext
    def update_result_command(result_id, updates):
        try:
            update_dict = {}
            for item in updates:
                key, value = item.split("=")
                # attempt to convert numeric values
                if value.replace(".", "", 1).isdigit():
                    value = float(value) if "." in value else int(value)
                update_dict[key] = value

            success = update_automated_result(result_id, **update_dict)
            if success:
                click.echo(f"Automated result updated: {get_automated_result(result_id).get_json()}")
            else:
                click.echo(f"No automated result found with ID {result_id}")
        except ValueError as e:
            click.echo(f"Error: {e}")
        except Exception:
            click.echo("Invalid update format. Use field=value")

    # Confirm Automated Result (flask confirm-result <result_id>)
    @app.cli.command("confirm-result")
    @click.argument("result_id", type=int)
    @with_appcontext
    def confirm_result_command(result_id):
        try:
            success = confirm_result(result_id)
            if success:
                click.echo("Automated result confirmed successfully.")
            else:
                click.echo(f"No automated result found with ID {result_id}")
        except Exception as e:
            click.echo(f"Error: {e}")

    # Delete Automated Result (flask delete-result <result_id>)
    @app.cli.command("delete-result")
    @click.argument("result_id", type=int)
    @with_appcontext
    def delete_result_command(result_id):
        success = delete_automated_result(result_id)
        if success:
            click.echo(f"Automated result {result_id} deleted successfully.")
        else:
            click.echo(f"No automated result found with ID {result_id}")


    
    app.app_context().push()
    return app
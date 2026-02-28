from flask import Flask, current_app
from flask_cors import CORS
from flask_sqlalchemy import SQLAlchemy
from flask.cli import with_appcontext
import click
from werkzeug.datastructures import FileStorage

from App.controllers.user import *
from App.controllers.judge import *
from App.controllers.admin import *
from App.controllers.institution import *
from App.controllers.leaderboard import *
from App.controllers.scoretaker import *
from App.controllers.season import *
from App.controllers.event import *
from App.controllers.pointsRules import *

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

#---------------------- SCORETAKER CLI TESTS ---------------------

    # Get Scoretaker Profile (flask scoretaker-get <user_id>)
    @app.cli.command("scoretaker-get")
    @click.argument("user_id", type=int)
    @with_appcontext
    def scoretaker_get_command(user_id):
        st = get_scoretaker(user_id)
        if not st:
            click.echo("No Scoretaker profile found.")
            return
        click.echo(st.get_json() if hasattr(st, "get_json") else f"Scoretaker(id={getattr(st, 'id', None)})")


    # List My Score Documents (flask score-docs-list <user_id>)
    @app.cli.command("score-docs-list")
    @click.argument("user_id", type=int)
    @with_appcontext
    def score_docs_list_command(user_id):
        docs = get_my_score_documents(user_id)
        if not docs:
            click.echo("No documents found.")
            return
        for d in docs:
            click.echo(d.get_json() if hasattr(d, "get_json") else str(d))


    # List My Score Documents JSON (flask score-docs-list-json <user_id>)
    @app.cli.command("score-docs-list-json")
    @click.argument("user_id", type=int)
    @with_appcontext
    def score_docs_list_json_command(user_id):
        docs = get_my_score_documents_json(user_id)
        if not docs:
            click.echo("No documents found.")
            return
        for d in docs:
            click.echo(d)


    # Upload Score Document (flask score-doc-upload <user_id> <file_path>)
    @app.cli.command("score-doc-upload")
    @click.argument("user_id", type=int)
    @click.argument("file_path", type=click.Path(exists=True, dir_okay=False))
    @with_appcontext
    def score_doc_upload_command(user_id, file_path):
        upload_folder = current_app.config.get("UPLOAD_FOLDER", "uploads")
        os.makedirs(upload_folder, exist_ok=True)

        with open(file_path, "rb") as f:
            fs = FileStorage(
                stream=f,
                filename=os.path.basename(file_path),
                content_type="application/octet-stream"
            )
            doc = upload_score_document(user_id, fs, upload_folder)

        click.echo("Uploaded document:")
        click.echo(doc.get_json() if hasattr(doc, "get_json") else str(doc))


    # Get Score Document By ID (flask score-doc-get <document_id>)
    @app.cli.command("score-doc-get")
    @click.argument("document_id", type=int)
    @with_appcontext
    def score_doc_get_command(document_id):
        doc = get_score_document(document_id)
        if not doc:
            click.echo("Document not found.")
            return
        click.echo(doc.get_json() if hasattr(doc, "get_json") else str(doc))


    # Delete Score Document (flask score-doc-delete <user_id> <document_id>)
    @app.cli.command("score-doc-delete")
    @click.argument("user_id", type=int)
    @click.argument("document_id", type=int)
    @with_appcontext
    def score_doc_delete_command(user_id, document_id):
        try:
            ok = delete_score_document(user_id, document_id)
            click.echo("Deleted." if ok else "Document not found.")
        except ValueError as e:
            click.echo(f"Error: {e}")
                    

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

    # Create Season (flask season-create <year>)
    @app.cli.command("season-create")
    @click.argument("year")
    @with_appcontext
    def season_create_command(year):
        try:
            s = create_season(year)
            click.echo("Created season:")
            click.echo(s.get_json() if hasattr(s, "get_json") else str(s))
        except ValueError as e:
            click.echo(f"Error: {e}")
            
    # Get Season by ID (flask season-get <season_id>)
    @app.cli.command("season-get")
    @click.argument("season_id", type=int)
    @with_appcontext
    def season_get_command(season_id):
        s = get_season(season_id)
        if not s:
            click.echo("Season not found.")
            return
        click.echo(s.get_json() if hasattr(s, "get_json") else str(s))
        
    # Get Season by Year (flask season-get-year <year>)
    @app.cli.command("season-get-year")
    @click.argument("year")
    @with_appcontext
    def season_get_year_command(year):
        s = get_season_by_year(year)
        if not s:
            click.echo("Season not found (or invalid year).")
            return
        click.echo(s.get_json() if hasattr(s, "get_json") else str(s))
    
    # List all Seasons (flask season-list)
    @app.cli.command("season-list")
    @with_appcontext
    def season_list_command():
        seasons = get_all_seasons()
        if not seasons:
            click.echo("No seasons found.")
            return
        for s in seasons:
            click.echo(s.get_json() if hasattr(s, "get_json") else str(s))

    
    # List all Seasons JSON (flask season-list-json)
    @app.cli.command("season-list-json")
    @with_appcontext
    def season_list_json_command():
        seasons = get_all_seasons_json()
        if not seasons:
            click.echo("No seasons found.")
            return
        for s in seasons:
            click.echo(s)
    
    #Update Season Year (flask season-update-year <season_id> <new_year>)
    @app.cli.command("season-update-year")
    @click.argument("season_id", type=int)
    @click.argument("new_year")
    @with_appcontext
    def season_update_year_command(season_id, new_year):
        try:
            ok = update_season_year(season_id, new_year)
            click.echo("Season updated." if ok else "Season not found.")
        except ValueError as e:
            click.echo(f"Error: {e}")
    
    # Delete Season (flask season-delete <season_id>)
    @app.cli.command("season-delete")
    @click.argument("season_id", type=int)
    @with_appcontext
    def season_delete_command(season_id):
        ok = delete_season(season_id)
        click.echo("Season deleted." if ok else "Season not found.")

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

    # Create Points Rule (flask points-rule-create <eventType> <conditionType> <conditionValue> <upperLimit> <lowerLimit> <seasonID>)
    @app.cli.command("points-rule-create")
    @click.argument("eventType")
    @click.argument("conditionType")
    @click.argument("conditionValue")
    @click.argument("upperLimit")
    @click.argument("lowerLimit")
    @click.argument("seasonID")
    @with_appcontext
    def points_rule_create_command(eventType, conditionType, conditionValue, upperLimit, lowerLimit, seasonID):
        try:
            rule = create_points_rule(eventType, conditionType, conditionValue, upperLimit, lowerLimit, seasonID)
            click.echo("Created points rule:")
            click.echo(rule.get_json() if hasattr(rule, "get_json") else str(rule))
        except ValueError as e:
            click.echo(f"Error: {e}")
            
    # Get Points Rule by ID (flask points-rule-get <pointsID>)
    @app.cli.command("points-rule-get")
    @click.argument("pointsID", type=int)
    @with_appcontext
    def points_rule_get_command(pointsID):
        rule = get_points_rule(pointsID)
        if not rule:
            click.echo("Points rule not found.")
            return
        click.echo(rule.get_json() if hasattr(rule, "get_json") else str(rule))



#------------------ AUTOMATED RESULTS CLI TESTS ------------------
    
    app.app_context().push()
    return app
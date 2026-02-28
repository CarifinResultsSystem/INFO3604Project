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

    #Get Scoretaker Profile ( flask scoretaker-get <user_id>)
    @click.command(name="scoretaker-get")
    @click.argument("user_id", type=int)
    @with_appcontext
    def scoretaker_get(user_id):
        st = get_scoretaker(user_id)
        if not st:
            print("No Scoretaker profile found.")
            return

        if hasattr(st, "get_json"):
            print(st.get_json())
        else:
            print(f"Scoretaker(id={getattr(st, 'id', None)})")@click.command(name="list-score-docs")
        @click.argument("user_id", type=int)
        @with_appcontext
        def list_score_docs(user_id):
            docs = get_score_document(user_id)
            if not docs:
                print("No documents found.")
                return

            for d in docs:
                print(d)
    
    # Upload Score Document (flask scoretaker-upload <user_id> <file_path>)
    @click.command(name="score-doc-upload")
    @click.argument("user_id", type=int)
    @click.argument("file_path", type=click.Path(exists=True, dir_okay=False))
    @with_appcontext
    def score_doc_upload(user_id, file_path):
        upload_folder = current_app.config.get("UPLOAD_FOLDER", "uploads")
        os.makedirs(upload_folder, exist_ok=True)

        with open(file_path, "rb") as f:
            fs = FileStorage(
                stream=f,
                filename=os.path.basename(file_path),
                content_type="application/octet-stream"
            )
            doc = upload_score_document(user_id, fs, upload_folder)

        print("Uploaded document:")
        print(doc.get_json() if hasattr(doc, "get_json") else doc)
        
       
    #List Score Documents (Raw) (flask scoretaker-list-docs <user_id>) 
    @click.command(name="score-docs-list")
    @click.argument("user_id", type=int)
    @with_appcontext
    def score_docs_list(user_id):
        docs = get_my_score_documents(user_id)
        if not docs:
            print("No documents found.")
            return

        for d in docs:
            print(d.get_json() if hasattr(d, "get_json") else d)
            
    #List Score Documents (json) (flask scoretaker-list-docs-json <user_id>)   
    @click.command(name="score-docs-list-json")
    @click.argument("user_id", type=int)
    @with_appcontext
    def score_docs_list_json(user_id):
        docs = get_my_score_documents_json(user_id)
        if not docs:
            print("No documents found.")
            return

        for d in docs:
            print(d)
    
    # Get Score Document By ID (flask scoretaker-get-doc <document_id>)
    @click.command(name="score-doc-get")
    @click.argument("document_id", type=int)
    @with_appcontext
    def score_doc_get(document_id):
        doc = get_score_document(document_id)
        if not doc:
            print("Document not found.")
            return

        print(doc.get_json() if hasattr(doc, "get_json") else doc)
        
    # Delete Score Document (flask scoretaker-delete-doc <user_id> <document_id>)
    @click.command(name="score-doc-delete")
    @click.argument("user_id", type=int)
    @click.argument("document_id", type=int)
    @with_appcontext
    def score_doc_delete(user_id, document_id):
        try:
            ok = delete_score_document(user_id, document_id)
            print("Deleted." if ok else "Document not found.")
        except ValueError as e:
            print(f"Error: {e}")
                    

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

    # Create Season (flask create-season <year>)
    @click.command(name="season-create")
    @click.argument("year")
    @with_appcontext
    def season_create(year):
        try:
            s = create_season(year)
            print("Created season:")
            print(s.get_json() if hasattr(s, "get_json") else s)
        except ValueError as e:
            print(f"Error: {e}")
            
    # Get Season by ID (flask get-season <season_id>)
    @click.command(name="season-get")
    @click.argument("season_id", type=int)
    @with_appcontext
    def season_get(season_id):
        s = get_season(season_id)
        if not s:
            print("Season not found.")
            return
        print(s.get_json() if hasattr(s, "get_json") else s)
        
    # Get Season by Year (flask get-season-year <year>)
    @click.command(name="season-get-year")
    @click.argument("year")
    @with_appcontext
    def season_get_year(year):
        s = get_season_by_year(year)
        if not s:
            print("Season not found (or invalid year).")
            return
        print(s.get_json() if hasattr(s, "get_json") else s)
    
    # Get All Seasons (flask get-all-seasons)
    @click.command(name="season-list")
    @with_appcontext
    def season_list():
        seasons = get_all_seasons()
        if not seasons:
            print("No seasons found.")
            return
        for s in seasons:
            print(s.get_json() if hasattr(s, "get_json") else s)

    # Get All Seasons (json) (flask get-all-seasons-json)
    @click.command(name="season-list-json")
    @with_appcontext
    def season_list_json():
        seasons = get_all_seasons_json()
        if not seasons:
            print("No seasons found.")
            return
        for s in seasons:
            print(s)
    
    # Update Season Year (flask update-season-year <season_id> <new_year>)
    @click.command(name="season-update-year")
    @click.argument("season_id", type=int)
    @click.argument("new_year")
    @with_appcontext
    def season_update_year(season_id, new_year):
        try:
            ok = update_season_year(season_id, new_year)
            if ok:
                print("Season updated.")
            else:
                print("Season not found.")
        except ValueError as e:
            print(f"Error: {e}")
    
    # Delete Season (flask delete-season <season_id>) 
    @click.command(name="season-delete")
    @click.argument("season_id", type=int)
    @with_appcontext
    def season_delete(season_id):
        ok = delete_season(season_id)
        print("Season deleted." if ok else "Season not found.")
    
    
    

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


#------------------ AUTOMATED RESULTS CLI TESTS ------------------
    
    app.app_context().push()
    return app
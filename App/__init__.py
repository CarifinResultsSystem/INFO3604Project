from flask import Flask, redirect, url_for
from flask_cors import CORS
from flask_sqlalchemy import SQLAlchemy

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
    def custom_unauthorized_response(error):
        return redirect(url_for('auth_views.login_page'))

    app.app_context().push()
    return app
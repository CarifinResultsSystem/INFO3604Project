from flask import Flask
from flask_cors import CORS
from flask_sqlalchemy import SQLAlchemy

from .views import views
from .config import load_config
from .database import *

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
    
    return app
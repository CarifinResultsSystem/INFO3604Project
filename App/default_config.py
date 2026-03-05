import os

SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL', 'sqlite:///temp-database.db')
SECRET_KEY = os.environ.get('SECRET_KEY', 'secret key')
import os

SQLALCHEMY_DATABASE_uri = os.environ.get('DATABASE_URL', 'sqlite:///temp-database.db')

if SQLALCHEMY_DATABASE_uri.startswith('postgres://'):
    SQLALCHEMY_DATABASE_uri = SQLALCHEMY_DATABASE_uri.replace('postgres://', 'postgresql://', 1)

SQLALCHEMY_DATABASE_URI = SQLALCHEMY_DATABASE_uri
SECRET_KEY = os.environ.get('SECRET_KEY', 'secret key')
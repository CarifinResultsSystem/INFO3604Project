#Imports go here
from .index import index_views
from .user import user_views
from .admin import setup_admin
from .auth import auth_views


#All imports must be listed in this list
views = [index_views, user_views, auth_views]
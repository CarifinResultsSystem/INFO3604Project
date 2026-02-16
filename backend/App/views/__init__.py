#Imports go here
from .index import index_views
from .user import user_views
from .admin import setup_admin


#All imports must be listed in this list
views = [index_views, user_views]
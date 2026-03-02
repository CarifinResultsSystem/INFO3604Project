#Imports go here
from .index import index_views
from .user import user_views
from .admin import setup_admin, admin_views
from .auth import auth_views
from .leaderboard import leaderboard_views
from .schedule import schedule_views
from .participant import participant_views
from .settings import settings_views
from .scoretaker import scoretaker_views
from .judge import judge_views
from .hr import hr_views


#All imports must be listed in this list
views = [index_views, 
         user_views, 
         auth_views, 
         leaderboard_views, 
         schedule_views, 
         participant_views,
         settings_views,
         scoretaker_views,
         judge_views,
         hr_views,
         admin_views]
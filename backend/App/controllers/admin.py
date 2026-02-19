from backend.App.models import User
from backend.App.database import db

def assignRole(userID, role):
    user = db.session.get(User, userID)
    user.role = role
    return None
    #function is subject to change with User Scripts
    
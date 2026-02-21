from sqlite3 import IntegrityError
from App.models import User
from App.database import db

#Create User
def create_user(username, role, email, password):
    newUser = User(username=username, role=role, email=email, password=password)

    try:
        db.session.add(newUser)
        db.session.commit()
        return newUser
    except ValueError:
        db.session.rollback()
        # raised by set_role if invalid role
        raise
    except IntegrityError:
        db.session.rollback()
        # likely unique constraint on username/email
        raise ValueError("Username or email already exists") 

#Read Users
def get_user(userID):
    return db.session.get(User, userID)

def get_user_by_username(username):
    result = db.session.execute(db.select(User).filter_by(username=username))
    return result.scalar_one_or_none()

def get_user_by_email(email):
    email = (email or "").lower().strip()
    result = db.session.execute(db.select(User).filter_by(email=email))
    return result.scalar_one_or_none()

def get_all_users():
    return db.session.scalars(db.select(User)).all()

def get_all_users_json():
    users = get_all_users()
    if not users:
        return []
    users = [user.get_json() for user in users]
    return users

def update_user(userID, username):
    user = get_user(userID)
    if user:
        user.username = username
        # user is already in the session; no need to re-add
        db.session.commit()
        return True
    return None

#Update Users
def update_user_username(userID, username):
    user = get_user(userID)
    if not user:
        return False

    user.username = (username or "").strip()
    if not user.username:
        raise ValueError("Username cannot be empty")

    try:
        db.session.commit()
        return True
    except IntegrityError:
        db.session.rollback()
        raise ValueError("Username already exists")
    
def update_user_email(userID, email):
    user = get_user(userID)
    if not user:
        return False

    user.email = (email or "").lower().strip()
    if not user.email:
        raise ValueError("Email cannot be empty")

    try:
        db.session.commit()
        return True
    except IntegrityError:
        db.session.rollback()
        raise ValueError("Email already exists")
    
def update_user_password(userID, newPassword):
    user = get_user(userID)
    if not user:
        return False

    if not newPassword:
        raise ValueError("Password cannot be empty")

    user.set_password(newPassword)
    db.session.commit()
    return True

def update_user_role(userID, role):
    user = get_user(userID)
    if not user:
        return False

    # will raise ValueError if invalid
    user.set_role(role)

    db.session.commit()
    return True

#Delete User
def delete_user(userID):
    user = get_user(userID)
    if user:
        db.session.delete(user)
        db.session.commit()
        return True
    return False

#Authenticate User 
def authenticate_user(username, password):
    user = get_user_by_username(username)
    if user and user.check_password(password):
        return user
    return None
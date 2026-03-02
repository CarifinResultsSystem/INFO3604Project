from flask_jwt_extended import create_access_token, jwt_required, JWTManager, get_jwt_identity, verify_jwt_in_request

from App.models import User
from App.database import db

def login(username, password):
    result = db.session.execute(db.select(User).filter_by(username=username))
    user = result.scalar_one_or_none()
    if user and user.check_password(password):
        return create_access_token(identity=str(user.userID))
    return None

def setup_jwt(app):
    jwt = JWTManager(app)

    @jwt.user_identity_loader
    def user_identity_lookup(identity):
        # store userID as string
        user_id = getattr(identity, "userID", identity)
        return str(user_id) if user_id is not None else None

    @jwt.user_lookup_loader
    def user_lookup_callback(_jwt_header, jwt_data):
        identity = jwt_data["sub"]
        try:
            user_id = int(identity)
        except (TypeError, ValueError):
            return None
        # This makes current_user available in routes after @jwt_required
        return db.session.get(User, user_id)

    return jwt

# Context processor to make 'is_authenticated' available to all templates
def add_auth_context(app):
    @app.context_processor
    def inject_user():
        try:
            verify_jwt_in_request()
            identity = get_jwt_identity()
            user_id = int(identity) if identity is not None else None
            current_user = db.session.get(User, user_id) if user_id is not None else None
            is_authenticated = current_user is not None
        except Exception as e:
            print(e)
            is_authenticated = False
            current_user = None
        return dict(is_authenticated=is_authenticated, current_user=current_user)

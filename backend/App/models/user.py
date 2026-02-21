from werkzeug.security import check_password_hash, generate_password_hash # type: ignore
from backend.App.database import db

class User(db.Model):
    __tablename__ = "users"
    
    userID = db.Column(db.Integer, primary_key=True)
    
    username =  db.Column(db.String(20), nullable=False, unique=True)
    role = db.Column(db.String(20), nullable=False, default='user')
    email = db.Column(db.String(120), nullable=False, unique=True, index=True)
    
    password = db.Column(db.String(256), nullable=False)
    
    #user roles that are allowed to be set, public is not a role as they dont log in
    ALLOWED_ROLES = {"admin", "judge", "hr", "scorekeeper", "user"}

    def __init__(self, username, role, email, password):
        self.username = username
        self.set_role(role)
        self.email = email.lower().strip()
        self.set_password(password)

    def get_json(self):
        return{
            'User ID': self.userID,
            'username': self.username,
            'role': self.role,
            'email': self.email
        }
        
    def set_role(self, role: str) -> None:
        role = (role or "user").lower().strip()
        if role not in self.ALLOWED_ROLES:
            raise ValueError(f"Invalid role: {role}")
        self.role = role

    def set_password(self, password):
        """Create hashed password."""
        self.password = generate_password_hash(password)
    
    def check_password(self, password):
        """Check hashed password."""
        return check_password_hash(self.password, password)
    
    def __repr__(self):
        return f"<User {self.email} ({self.role})>"
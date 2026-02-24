from .user import User
from App.database import db

class Admin(User):
    __tablename__ = 'admin'
    
    userID = db.Column(
        db.Integer,
        db.ForeignKey("users.userID"),
        primary_key=True
    )
    
    __mapper_args__ = {
        'polymorphic_identity': 'admin'
    }
    
    def __init__(self, username, password):
        super().__init__(username, password)
        
    def get_json(self):
        return{
            'id': self.id,
            'username': self.username,
            'admin_id': self.admin_id
        }
from .user import User
from backend.App.database import db

class Admin(User):
    __tablename__ = 'admin'
    
    adminID = db.Column(db.Integer, primary_key=True)
    
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
from App.database import db

class Institution(db.Model):
    
    institutionID = db.Column(db.Integer, primary_key=True)
    insName = db.Column(db.String(256), nullable=False)
    insTotalPoints = db.Column(db.Integer)
    insRank = db.Column(db.Integer)
    
    def __init__(self, insName):
        self.insName = insName
        self.insTotalPoints = 0
        
    def get_json(self):
        return{
            'insName': self.insName,
            'insTotalPoints': self.insTotalPoints
        }
from App.database import db

class Institution(db.Model):

    institutionID = db.Column(db.Integer, primary_key=True)
    insName = db.Column(db.String(256), nullable=False)
    insLocation = db.Column(db.String(256), nullable=False)
    insTotalPoints = db.Column(db.Integer, default=0)
    insRank = db.Column(db.Integer)

    def __init__(self, insName, insLocation):
        self.insName = insName
        self.insLocation = insLocation

    def get_json(self):
        return {
            "insName": self.insName,
            "insLocation": self.insLocation,
            "insTotalPoints": self.insTotalPoints,
            "insRank": self.insRank
        }
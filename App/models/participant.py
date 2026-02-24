from App.database import db


class Participant(db.Model):
    __tablename__ = "participants"

    participantID = db.Column(db.String(50), primary_key=True)

    firstName = db.Column(db.String(100), nullable=False)
    lastName = db.Column(db.String(100), nullable=False)
    gender = db.Column(db.String(20), nullable=False)
    dateOfBirth = db.Column(db.String(20), nullable=False)
    location = db.Column(db.String(256), nullable=False)

    institutionID = db.Column(
        db.Integer,
        db.ForeignKey("institution.institutionID"),
        nullable=False
    )

    institution = db.relationship(
        "Institution",
        backref=db.backref("participants", lazy=True, cascade="all, delete-orphan"),
        lazy=True,
    )

    def __init__(self, participantID, firstName, lastName, gender, dateOfBirth, location, institutionID):
        self.participantID = participantID
        self.firstName = firstName
        self.lastName = lastName
        self.gender = gender
        self.dateOfBirth = dateOfBirth
        self.location = location
        self.institutionID = institutionID

    def get_json(self):
        return {
            "participantID": self.participantID,
            "firstName": self.firstName,
            "lastName": self.lastName,
            "gender": self.gender,
            "dateOfBirth": self.dateOfBirth,
            "location": self.location,
            "institutionID": self.institutionID,
            "institutionName": self.institution.insName if self.institution else None
        }
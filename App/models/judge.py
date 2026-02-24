from App.database import db


class Judge(db.Model):
    __tablename__ = "judges"

    userID = db.Column(
        db.Integer,
        db.ForeignKey("users.userID"),
        primary_key=True
    )

    user = db.relationship(
        "User",
        backref=db.backref("judge_profile", uselist=False),
        lazy=True,
    )

    def __init__(self, userID):
        self.userID = userID

    def get_json(self):
        return {
            "userID": self.userID,
            "username": self.user.username if self.user else None,
            "email": self.user.email if self.user else None,
            "role": "judge"
        }
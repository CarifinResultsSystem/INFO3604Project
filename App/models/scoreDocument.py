import os
import uuid
from datetime import datetime
from werkzeug.utils import secure_filename  # type: ignore

from App.database import db 

class ScoreDocument(db.Model):
    """
    Mirrors UML ScoreDocument:
    - documentID
    - file (we store metadata + path)
    """
    __tablename__ = "score_documents"

    documentID = db.Column(db.Integer, primary_key=True)

    originalFilename = db.Column(db.String(255), nullable=False)
    storedFilename = db.Column(db.String(255), nullable=False)
    storedPath = db.Column(db.String(512), nullable=False)

    uploadedOn = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    # owner
    scoretakerID = db.Column(
        db.Integer,
        db.ForeignKey("scoretakers.userID"),
        nullable=False,
        index=True,
    )

    scoretaker = db.relationship(
        "Scoretaker",
        backref=db.backref("score_documents", lazy=True, cascade="all, delete-orphan"),
        lazy=True,
    )

    def get_json(self):
        return {
            "documentID": self.documentID,
            "originalFilename": self.originalFilename,
            "storedFilename": self.storedFilename,
            "uploadedOn": self.uploadedOn.isoformat() if self.uploadedOn else None,
            "scoretakerID": self.scoretakerID,
        }
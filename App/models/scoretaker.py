import os
import uuid
from datetime import datetime
from werkzeug.utils import secure_filename  # type: ignore

from App.database import db


class Scoretaker(db.Model):
    """
    Scoretaker profile table: 1-to-1 with User.
    This approach avoids needing SQLAlchemy inheritance changes in User.
    """
    __tablename__ = "scoretakers"

    userID = db.Column(db.Integer, db.ForeignKey("users.userID"), primary_key=True)

    # 1:1 relationship back to User
    user = db.relationship(
        "User",
        backref=db.backref("scoretaker_profile", uselist=False),
        lazy=True,
    )

    def __init__(self, userID: int):
        self.userID = userID

    @staticmethod
    def get_or_create_for_user(user_id: int) -> "Scoretaker":
        st = db.session.get(Scoretaker, user_id)
        if st is None:
            st = Scoretaker(userID=user_id)
            db.session.add(st)
        return st

    def upload_score_document(self, file_storage, upload_folder: str) -> "ScoreDocument":
        """
        UML: uploadScoreDocument(ScoreDocument): ScoreDocument

        file_storage: Werkzeug FileStorage, e.g. request.files["file"]
        upload_folder: where files are stored on disk
        """
        if file_storage is None or not getattr(file_storage, "filename", ""):
            raise ValueError("No file provided.")

        os.makedirs(upload_folder, exist_ok=True)

        original_name = secure_filename(file_storage.filename)
        if original_name == "":
            raise ValueError("Invalid filename.")

        ext = os.path.splitext(original_name)[1].lower()

        stored_name = f"{uuid.uuid4().hex}{ext}"
        stored_path = os.path.join(upload_folder, stored_name)

        file_storage.save(stored_path)

        doc = ScoreDocument(
            originalFilename=original_name,
            storedFilename=stored_name,
            storedPath=stored_path,
            uploadedOn=datetime.utcnow(),
            scoretakerID=self.userID,
        )
        db.session.add(doc)
        return doc


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
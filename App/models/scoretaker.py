import os
import uuid
from datetime import datetime
from werkzeug.utils import secure_filename  # type: ignore

from App.database import db
from App.models.scoreDocument import ScoreDocument


class Scoretaker(db.Model):
    __tablename__ = "scoretakers"

    userID = db.Column(db.Integer, db.ForeignKey("users.userID"), primary_key=True)

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

    def upload_score_document(self, file_storage, seasonID: int) -> "ScoreDocument":
        """Read the uploaded file into memory and persist it as LargeBinary in the DB."""
        if file_storage is None or not getattr(file_storage, "filename", ""):
            raise ValueError("No file provided.")

        if not seasonID:
            raise ValueError("Season is required.")

        original_name = secure_filename(file_storage.filename)
        if original_name == "":
            raise ValueError("Invalid filename.")

        ext = os.path.splitext(original_name)[1].lower()
        stored_name = f"{uuid.uuid4().hex}{ext}"

        file_bytes = file_storage.read()

        doc = ScoreDocument(
            originalFilename=original_name,
            storedFilename=stored_name,
            fileData=file_bytes,
            uploadedOn=datetime.utcnow(),
            scoretakerID=self.userID,
            seasonID=int(seasonID),
        )

        db.session.add(doc)
        db.session.flush()

        return doc
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

    def upload_score_document(self, file_storage, upload_folder: str) -> "ScoreDocument":
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

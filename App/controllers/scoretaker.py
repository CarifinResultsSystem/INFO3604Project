import os
from App.database import db
from App.models import Scoretaker, ScoreDocument


# Get Scoretaker Profile
def get_scoretaker(userID: int):
    return db.session.get(Scoretaker, userID)

# Upload Score Document
def upload_score_document(userID: int, file_storage, upload_folder: str):
    """
    userID: the current logged in user id
    """
    st = Scoretaker.get_or_create_for_user(userID)

    doc = st.upload_score_document(file_storage=file_storage, upload_folder=upload_folder)

    db.session.commit()
    return doc

# Read Score Documents
def get_score_document(documentID: int):
    return db.session.get(ScoreDocument, documentID)

def get_my_score_documents(userID: int):
    st = get_scoretaker(userID)
    if not st:
        return []
    return st.score_documents

def get_my_score_documents_json(userID: int):
    docs = get_my_score_documents(userID)
    if not docs:
        return []
    return [d.get_json() for d in docs]

# Delete Score Document
def delete_score_document(userID: int, documentID: int):
    """
    Deletes a score document if it belongs to this user
    """
    doc = get_score_document(documentID)
    if not doc:
        return False

    if doc.scoretakerID != userID:
        raise ValueError("Forbidden: you do not own this document")

    try:
        if doc.storedPath and os.path.exists(doc.storedPath):
            os.remove(doc.storedPath)
    except Exception:
        pass

    db.session.delete(doc)
    db.session.commit()
    return True
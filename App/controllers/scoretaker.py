from App.database import db
from App.models import Scoretaker, ScoreDocument, Season


# Get Scoretaker Profile
def get_scoretaker(userID: int):
    return db.session.get(Scoretaker, userID)

# Upload Score Document
def upload_score_document(userID: int, file_storage, seasonID: int):
    st = Scoretaker.get_or_create_for_user(userID)

    season = db.session.get(Season, int(seasonID))
    if not season:
        raise ValueError("Invalid season selected")

    doc = st.upload_score_document(
        file_storage=file_storage,
        seasonID=season.seasonID,
    )

    db.session.commit()
    return doc

# Read Score Documents
def get_score_document(documentID: int):
    return db.session.get(ScoreDocument, documentID)

def get_my_score_documents(userID: int):
    # Use get_or_create so a missing Scoretaker row never silently returns []
    # This is safe — if no row exists it creates one (with no documents) rather than returning nothing
    st = Scoretaker.get_or_create_for_user(userID)
    db.session.flush()  # ensure the new row is visible within this session if just created
    return list(st.score_documents)

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

    db.session.delete(doc)
    db.session.commit()
    return True
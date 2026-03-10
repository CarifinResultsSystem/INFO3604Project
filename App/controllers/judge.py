from App.database import db
from App.models import Judge, AutomatedResult, ScoreDocument


# Get Judge Profile
def get_judge(userID):
    return db.session.get(Judge, userID)


# Edit Results
def edit_results(judgeID, resultID, **kwargs):
    judge = get_judge(judgeID)
    if not judge:
        raise ValueError("Judge not found")

    result = db.session.get(AutomatedResult, resultID)
    if not result:
        raise ValueError("Automated result not found")

    for key, value in kwargs.items():
        if hasattr(result, key) and value is not None:
            setattr(result, key, value)

    db.session.commit()
    return result


# Confirm Score
def confirm_score(judgeID, resultID):
    judge = get_judge(judgeID)
    if not judge:
        raise ValueError("Judge not found")

    result = db.session.get(AutomatedResult, resultID)
    if not result:
        raise ValueError("Automated result not found")

    result.confirmed = True
    db.session.commit()
    return True

# Get Score Documents
def get_score_document(documentID):
    return db.session.get(ScoreDocument, documentID)

def get_all_score_documents():
    return db.session.scalars(db.select(ScoreDocument)).all()

def get_unconfirmed_documents():
    return db.session.scalars(db.select(ScoreDocument).filter_by(confirmed=False)).all()

def get_unconfirmed_documents_count():
    return db.session.scalar(db.select(db.func.count()).select_from(ScoreDocument).filter_by(confirmed=False))

# View Automated Results
def get_automated_result(resultID):
    return db.session.get(AutomatedResult, resultID)

def get_all_automated_results():
    return db.session.scalars(db.select(AutomatedResult)).all()

def get_all_automated_results_json():
    results = get_all_automated_results()
    if not results:
        return []
    return [r.get_json() for r in results]
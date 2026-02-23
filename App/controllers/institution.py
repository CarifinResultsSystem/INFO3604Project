from App.models import Institution
from App.database import db

def create_institution(insName):
    newInstitution = Institution(insName=insName)
    db.session.add(newInstitution)
    db.session.commit()
    return newInstitution

def get_institution_by_name(insName):
    return Institution.query.filter_by(insName=insName).first()

def get_institution(institutionID):
    return db.session.get(Institution, institutionID)

def get_all_institutions():
    return db.session.scalars(db.select(Institution)).all()

def get_all_institutions_json():
    institutions = get_all_institutions()
    if not institutions:
        return []
    institutions = [institution.get_json() for institution in institutions]
    return institutions
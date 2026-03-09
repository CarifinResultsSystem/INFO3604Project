import os
from flask import Blueprint, render_template, url_for
from flask_jwt_extended import jwt_required, current_user
from App.controllers import get_score_document, get_all_score_documents, get_unconfirmed_documents, get_unconfirmed_documents_count
from App.models import ScoreDocument
import pandas as pd

judge_views = Blueprint('judge_views', __name__, template_folder='../templates')

@judge_views.route('/judge/')
@jwt_required()
def judge_dashboard():
    unconfirmed_docs_count = get_unconfirmed_documents_count()
    unconfirmed_docs = get_unconfirmed_documents()
    errors = 0
    
    for doc in unconfirmed_docs:
        doc_df = pd.read_excel(doc.storedPath)
        print(doc_df)
        print(doc_df.shape)
        
        
    return render_template('judge/judge.html', user=current_user, unconfirmed_docs_count=unconfirmed_docs_count)

@judge_views.route('/judge/review')
@jwt_required()
def review_scores():
    documents = get_all_score_documents()
    
    docs_data = []
    for d in documents:
        ext = os.path.splitext(d.originalFilename)[1].lstrip('.').upper() if d.originalFilename else ''
        docs_data.append({
            "id":            d.documentID,
            "filename":      d.originalFilename or '—',
            "storedFilename": d.storedFilename,
            "uploadedAt":    d.uploadedOn.strftime("%b %d, %Y · %H:%M") if d.uploadedOn else "—",
            "uploadedAtRaw": d.uploadedOn.isoformat() if d.uploadedOn else "",
            "fileType":      ext or "FILE",
            "viewUrl":       url_for('scoretaker_views.view_document', documentID=d.documentID),
            "deleteUrl":     url_for('scoretaker_views.delete_document', documentID=d.documentID),
        })

    # Sort newest first by default
    docs_data.sort(key=lambda x: x["uploadedAtRaw"], reverse=True)
    
    return render_template('judge/review.html', documents=docs_data)

@judge_views.route('/judge/review/<int:documentID>', methods=['GET'])
@jwt_required()
def review_score_document(documentID):
    document = get_score_document(documentID)
    
    ext = os.path.splitext(document.originalFilename)[1].lstrip('.').upper() if document.originalFilename else ''
    doc_data = ({
        "id":            document.documentID,
        "filename":      document.originalFilename or '—',
        "storedFilename": document.storedFilename,
        "uploadedAt":    document.uploadedOn.strftime("%b %d, %Y · %H:%M") if document.uploadedOn else "—",
        "uploadedAtRaw": document.uploadedOn.isoformat() if document.uploadedOn else "",
        "fileType":      ext or "FILE",
        "viewUrl":       url_for('scoretaker_views.view_document', documentID=document.documentID),
        "deleteUrl":     url_for('scoretaker_views.delete_document', documentID=document.documentID),
    })
    
    try:
        df = pd.read_excel(document.storedPath)
        table_data = {
            'columns': df.columns.tolist(),
            'rows': df.values.tolist(),
            'headers': df.columns.tolist()
        }
    except Exception as e:
        table_data = {
            'columns': ['Error'],
            'rows': [[f'Could not load file: {str(e)}']],
            'headers': ['Error']
        }
    
    return render_template('judge/review_document.html', document=doc_data, table_data=table_data)


@judge_views.route('/judge/review/<int:documentID>/edit', methods=['GET'])
@jwt_required()
def edit_score_document(documentID):
    document = get_score_document(documentID)
    
    ext = os.path.splitext(document.originalFilename)[1].lstrip('.').upper() if document.originalFilename else ''
    doc_data = ({
        "id":            document.documentID,
        "filename":      document.originalFilename or '—',
        "storedFilename": document.storedFilename,
        "uploadedAt":    document.uploadedOn.strftime("%b %d, %Y · %H:%M") if document.uploadedOn else "—",
        "uploadedAtRaw": document.uploadedOn.isoformat() if document.uploadedOn else "",
        "fileType":      ext or "FILE",
        "viewUrl":       url_for('scoretaker_views.view_document', documentID=document.documentID),
        "deleteUrl":     url_for('scoretaker_views.delete_document', documentID=document.documentID),
    })
    
    try:
        df = pd.read_excel(document.storedPath)
        table_data = {
            'columns': df.columns.tolist(),
            'rows': df.values.tolist(),
            'headers': df.columns.tolist()
        }
    except Exception as e:
        table_data = {
            'columns': ['Error'],
            'rows': [[f'Could not load file: {str(e)}']],
            'headers': ['Error']
        }
    
    return render_template('judge/edit_document.html', document=doc_data, table_data=table_data)

#modified from scoretaker archives
@judge_views.route('/judge/archives')
@jwt_required()
def archives():
    documents = get_all_score_documents()

    docs_data = []
    for d in documents:
        ext = os.path.splitext(d.originalFilename)[1].lstrip('.').upper() if d.originalFilename else ''
        docs_data.append({
            "id":            d.documentID,
            "filename":      d.originalFilename or '—',
            "storedFilename": d.storedFilename,
            "uploadedAt":    d.uploadedOn.strftime("%b %d, %Y · %H:%M") if d.uploadedOn else "—",
            "uploadedAtRaw": d.uploadedOn.isoformat() if d.uploadedOn else "",
            "fileType":      ext or "FILE",
            "viewUrl":       url_for('scoretaker_views.view_document', documentID=d.documentID),
            "deleteUrl":     url_for('scoretaker_views.delete_document', documentID=d.documentID),
        })

    # Sort newest first by default
    docs_data.sort(key=lambda x: x["uploadedAtRaw"], reverse=True)

    return render_template(
        'judge/archives.html',
        documents=docs_data,
        total=len(docs_data),
        user=current_user
    )
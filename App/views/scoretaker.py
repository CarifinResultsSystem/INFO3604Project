import os
from flask import Blueprint, render_template, request, redirect, url_for, flash, current_app
from flask_jwt_extended import jwt_required, current_user

from App.controllers import (
    upload_score_document,
    get_my_score_documents,
    delete_score_document
)

scoretaker_views = Blueprint('scoretaker_views', __name__, url_prefix='/scoretaker')


# Scoretaker Dashboard
@scoretaker_views.route('/', methods=['GET'])
@jwt_required()
def scoretaker_dashboard():

    documents = get_my_score_documents(current_user.userID)

    total_uploads = len(documents)

    submitted_for_review = len(
        [d for d in documents if getattr(d, "status", "") == "submitted"]
    )

    upload_errors = len(
        [d for d in documents if getattr(d, "hasError", False)]
    )

    return render_template(
        'scoretaker/scoretaker.html',
        total_uploads=total_uploads,
        submitted_for_review=submitted_for_review,
        upload_errors=upload_errors,
        user=current_user
    )


# Upload Scores
@scoretaker_views.route('/upload', methods=['GET', 'POST'])
@jwt_required()
def upload_scores():

    if request.method == 'POST':

        files = request.files.getlist('files')

        if not files or files[0].filename == '':
            flash("No files selected.", "error")
            return redirect(url_for('scoretaker_views.upload_scores'))

        upload_folder = os.path.join(
            current_app.config.get("UPLOAD_FOLDER", "uploads")
        )

        success_count = 0
        error_count = 0

        for file in files:
            try:
                if not file.filename.lower().endswith(".xml"):
                    error_count += 1
                    continue

                upload_score_document(
                    userID=current_user.userID,
                    file_storage=file,
                    upload_folder=upload_folder
                )

                success_count += 1

            except Exception:
                error_count += 1

        if success_count > 0:
            flash(f"{success_count} file(s) uploaded successfully.", "success")

        if error_count > 0:
            flash(f"{error_count} file(s) failed to upload.", "error")

        return redirect(url_for('scoretaker_views.scoretaker_dashboard'))

    return render_template('scoretaker/uploadScores.html')


# Delete Document
@scoretaker_views.route('/delete/<int:documentID>', methods=['POST'])
@jwt_required()
def delete_document(documentID):

    try:
        delete_score_document(current_user.userID, documentID)
        flash("Document deleted.", "success")
    except Exception as e:
        flash(str(e), "error")

    return redirect(url_for('scoretaker_views.scoretaker_dashboard'))
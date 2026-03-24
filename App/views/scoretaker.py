import os
from datetime import date, datetime
from flask import Blueprint, render_template, request, redirect, url_for, flash, current_app, send_file, abort
from flask_jwt_extended import jwt_required, current_user

from flask import send_file
import openpyxl
from io import BytesIO

from App.models import Event, Institution
from App.models.challenge import Challenge

from App.controllers import (
    upload_score_document,
    get_my_score_documents,
    delete_score_document
)

scoretaker_views = Blueprint('scoretaker_views', __name__, url_prefix='/scoretaker')

ALLOWED_EXTENSIONS = {
    ".xml", ".xlsx", ".xls", ".xlsm", ".xlsb",
    ".xlam", ".xltx", ".xltm", ".csv", ".ods"
}


def _allowed(filename: str) -> bool:
    return os.path.splitext(filename.lower())[1] in ALLOWED_EXTENSIONS


# ── Dashboard ─────────────────────────────────────────────────────────────────

@scoretaker_views.route('/', methods=['GET'])
@jwt_required()
def scoretaker_dashboard():
    documents = get_my_score_documents(current_user.userID)
    today = date.today()

    total_uploads  = len(documents)
    uploaded_today = len([
        d for d in documents
        if d.uploadedOn and d.uploadedOn.date() == today
    ])

    return render_template(
        'scoretaker/scoretaker.html',
        total_uploads=total_uploads,
        uploaded_today=uploaded_today,
        user=current_user
    )


# ── Upload Scores ─────────────────────────────────────────────────────────────

@scoretaker_views.route('/upload', methods=['GET', 'POST'])
@jwt_required()
def upload_scores():
    if request.method == 'POST':
        files = request.files.getlist('files')

        if not files or files[0].filename == '':
            flash("No files selected.", "error")
            return redirect(url_for('scoretaker_views.upload_scores'))

        upload_folder = current_app.config.get("UPLOAD_FOLDER", "uploads")
        os.makedirs(upload_folder, exist_ok=True)

        success_count = 0
        error_count   = 0

        for file in files:
            try:
                if not _allowed(file.filename):
                    flash(f"'{file.filename}' is not a supported format.", "error")
                    error_count += 1
                    continue

                upload_score_document(
                    userID=current_user.userID,
                    file_storage=file,
                    upload_folder=upload_folder
                )
                success_count += 1

            except Exception as e:
                flash(f"Error uploading '{file.filename}': {e}", "error")
                error_count += 1

        if success_count:
            flash(f"{success_count} file(s) uploaded successfully.", "success")
        if error_count:
            flash(f"{error_count} file(s) failed to upload.", "error")

        # Redirect to archives so the user can immediately see the uploaded files
        return redirect(url_for('scoretaker_views.archives'))

    return render_template('scoretaker/uploadScores.html', user=current_user)


# ── Archives ──────────────────────────────────────────────────────────────────

@scoretaker_views.route('/archives', methods=['GET'])
@jwt_required()
def archives():
    documents = get_my_score_documents(current_user.userID)

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
        'scoretaker/archives.html',
        documents=docs_data,
        total=len(docs_data),
        user=current_user
    )


# ── View / Download ───────────────────────────────────────────────────────────

@scoretaker_views.route('/document/<int:documentID>', methods=['GET'])
@jwt_required()
def view_document(documentID):
    from App.models import ScoreDocument
    doc = ScoreDocument.query.filter_by(
        documentID=documentID,
        scoretakerID=current_user.userID
    ).first_or_404()

    if not os.path.exists(doc.storedPath):
        abort(404)

    return send_file(
        doc.storedPath,
        as_attachment=False,
        download_name=doc.originalFilename
    )


# ── Delete ────────────────────────────────────────────────────────────────────

@scoretaker_views.route('/delete/<int:documentID>', methods=['POST'])
@jwt_required()
def delete_document(documentID):
    try:
        delete_score_document(current_user.userID, documentID)
        flash("Document deleted.", "success")
    except Exception as e:
        flash(str(e), "error")

    return redirect(url_for('scoretaker_views.archives'))


@scoretaker_views.route("/scoretaker/template")
@jwt_required()
def download_template():

    from App.models import PointsRules

    institutions = Institution.query.order_by(Institution.insName.asc()).all()
    events = Event.query.order_by(Event.eventName.asc()).all()
    challenges = Challenge.query.order_by(Challenge.challengeName.asc()).all()

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Scores Template"

    # ---- HEADER ----
    ws.cell(row=1, column=1, value="Event / Challenge")

    col = 2
    for inst in institutions:
        ws.cell(row=1, column=col, value=inst.insName)
        col += 1

    row = 2

    # ---- CHALLENGES WITH EVENTS ----
    for ch in challenges:
        # Challenge Title (BOLD)
        cell = ws.cell(row=row, column=1, value=f"Challenge: {ch.challengeName}")
        cell.font = openpyxl.styles.Font(bold=True)
        row += 1

        for ev in ch.events:
            # Event Name (ITALIC)
            cell = ws.cell(row=row, column=1, value=f"   Event: {ev.eventName}")
            cell.font = openpyxl.styles.Font(italic=True)
            row += 1

            rules = PointsRules.query.filter_by(eventID=ev.eventID).all()

            for r in rules:
                if r.ruleType == "individual":
                    label = f"      - Individual: {r.label or f'Place {r.placement}'}"
                else:
                    label = f"      - Team: {r.category} ({r.label})"

                ws.cell(row=row, column=1, value=label)
                row += 1

        row += 1  # spacing

    # ---- EVENTS NOT IN ANY CHALLENGE ----
    challenge_event_ids = {ev.eventID for ch in challenges for ev in ch.events}

    for ev in events:
        if ev.eventID in challenge_event_ids:
            continue

        cell = ws.cell(row=row, column=1, value=f"Event: {ev.eventName}")
        cell.font = openpyxl.styles.Font(italic=True)
        row += 1

        rules = PointsRules.query.filter_by(eventID=ev.eventID).all()

        for r in rules:
            if r.ruleType == "individual":
                label = f"   - Individual: {r.label or f'Place {r.placement}'}"
            else:
                label = f"   - Team: {r.category} ({r.label})"

            ws.cell(row=row, column=1, value=label)
            row += 1

        row += 1

    # ---- TOTAL + RANKING ----
    row += 1

    total_row = row
    ws.cell(row=total_row, column=1, value="TOTAL POINTS")

    rank_row = total_row + 1
    ws.cell(row=rank_row, column=1, value="RANKING")

    # Optional: formulas (Excel will calculate)
    for col in range(2, len(institutions) + 2):
        col_letter = openpyxl.utils.get_column_letter(col)

        # Sum all above rows
        ws.cell(
            row=total_row,
            column=col,
            value=f"=SUM({col_letter}2:{col_letter}{total_row-1})"
        )

        # Ranking formula
        ws.cell(
            row=rank_row,
            column=col,
            value=f"=RANK({col_letter}{total_row},$B${total_row}:$"
                  f"{openpyxl.utils.get_column_letter(len(institutions)+1)}${total_row},0)"
        )

    # ---- AUTO WIDTH ----
    for col_cells in ws.columns:
        max_length = 0
        col_letter = col_cells[0].column_letter

        for cell in col_cells:
            if cell.value:
                max_length = max(max_length, len(str(cell.value)))

        ws.column_dimensions[col_letter].width = max_length + 3

    # Save
    output = BytesIO()
    wb.save(output)
    output.seek(0)

    return send_file(
        output,
        as_attachment=True,
        download_name="score_template.xlsx",
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
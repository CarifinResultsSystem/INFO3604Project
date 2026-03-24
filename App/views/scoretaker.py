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
    from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
    from openpyxl.utils import get_column_letter

    institutions = Institution.query.order_by(Institution.insName.asc()).all()
    events       = Event.query.order_by(Event.eventName.asc()).all()
    challenges   = Challenge.query.order_by(Challenge.challengeName.asc()).all()

    FONT_NAME      = "Arial"
    C_CHALLENGE_BG = "0B3D91"  # Deep blue
    C_EVENT_BG     = "1E5BB8"  # Medium blue
    C_RULE_BG      = "E3F2FD"  # Very light blue (background for rules)
    C_INST_HDR_BG  = "0A2A66"  # Dark navy blue

    C_TOTAL_BG     = "1C1C1C"  # Keep neutral dark (optional: "0D47A1")
    C_RANK_BG      = "424242"  # Keep gray or change to "1565C0"

    C_INPUT_BG     = "EAF4FF"  # Light blue input cells
    C_WHITE        = "FFFFFF"
    C_LIGHT_BORDER = "90CAF9"  # Light blue border
    C_GAP          = "E3F2FD"  # Match rule background

    def fill(hex_color):
        return PatternFill("solid", start_color=hex_color, fgColor=hex_color)

    def font(bold=False, italic=False, color=C_WHITE, size=10, name=FONT_NAME):
        return Font(name=name, bold=bold, italic=italic, color=color, size=size)

    def border_all(color=C_LIGHT_BORDER, style="thin"):
        s = Side(border_style=style, color=color)
        return Border(left=s, right=s, top=s, bottom=s)

    def border_bottom(color=C_LIGHT_BORDER, style="thin"):
        s = Side(border_style=style, color=color)
        return Border(bottom=s)

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Scores Template"

    n_inst = len(institutions)
    ws.column_dimensions["A"].width = 40
    for i in range(2, n_inst + 2):
        ws.column_dimensions[get_column_letter(i)].width = 14

    row = 1

    def write_inst_header_row():
        nonlocal row
        ws.row_dimensions[row].height = 28
        lbl = ws.cell(row=row, column=1, value="Rule")
        lbl.font      = font(bold=True, size=10, color="C9A6FF")
        lbl.fill      = fill(C_INST_HDR_BG)
        lbl.alignment = Alignment(horizontal="left", vertical="center", indent=1)
        for i, inst in enumerate(institutions, start=2):
            c = ws.cell(row=row, column=i, value=inst.insName)
            c.font      = font(bold=True, size=10, color=C_WHITE)
            c.fill      = fill(C_INST_HDR_BG)
            c.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
        row += 1

    def write_challenge_row(name):
        nonlocal row
        ws.row_dimensions[row].height = 26
        lbl = ws.cell(row=row, column=1, value=name.upper())
        lbl.font      = font(bold=True, size=12, color=C_WHITE)
        lbl.fill      = fill(C_CHALLENGE_BG)
        lbl.alignment = Alignment(horizontal="left", vertical="center", indent=1)
        for c in range(2, n_inst + 2):
            ws.cell(row=row, column=c).fill = fill(C_CHALLENGE_BG)
        row += 1

    def write_event_row(name):
        nonlocal row
        ws.row_dimensions[row].height = 20
        lbl = ws.cell(row=row, column=1, value=name)
        lbl.font      = font(bold=False, italic=True, size=10, color=C_WHITE)
        lbl.fill      = fill(C_EVENT_BG)
        lbl.alignment = Alignment(horizontal="left", vertical="center", indent=2)
        for c in range(2, n_inst + 2):
            ws.cell(row=row, column=c).fill = fill(C_EVENT_BG)
        row += 1

    def write_rule_row(label):
        nonlocal row
        ws.row_dimensions[row].height = 18
        lbl = ws.cell(row=row, column=1, value=label)
        lbl.font = Font(name=FONT_NAME, size=9, italic=True, color="0D47A1")
        lbl.fill      = fill(C_RULE_BG)
        lbl.alignment = Alignment(horizontal="left", vertical="center", indent=4)
        lbl.border    = border_bottom()
        for c in range(2, n_inst + 2):
            cell               = ws.cell(row=row, column=c)
            cell.fill          = fill(C_INPUT_BG)
            cell.border        = border_all()
            cell.alignment     = Alignment(horizontal="center", vertical="center")
            cell.number_format = "0.00"
        row += 1

    def write_gap():
        nonlocal row
        ws.row_dimensions[row].height = 8
        for c in range(1, n_inst + 2):
            ws.cell(row=row, column=c).fill = fill(C_GAP)
        row += 1

    def write_rules_for_event(event_id):
        rules = PointsRules.query.filter_by(eventID=event_id).all()
        if rules:
            for r in rules:
                if r.ruleType == "individual":
                    label = f"Place {r.placement}" + (f"  -  {r.label}" if r.label else "")
                else:
                    label = f"{r.category}  -  {r.label}"
                write_rule_row(label)
        else:
            write_rule_row("(no rules configured)")

    score_rows = []
    challenge_event_ids = set()

    for ch in challenges:
        write_inst_header_row()
        write_challenge_row(ch.challengeName)
        for ev in ch.events:
            challenge_event_ids.add(ev.eventID)
            write_event_row(ev.eventName)
            start = row
            write_rules_for_event(ev.eventID)
            score_rows.extend(range(start, row))
        write_gap()

    orphans = [e for e in events if e.eventID not in challenge_event_ids]
    if orphans:
        write_inst_header_row()
        write_challenge_row("Other Events")
        for ev in orphans:
            write_event_row(ev.eventName)
            start = row
            write_rules_for_event(ev.eventID)
            score_rows.extend(range(start, row))
        write_gap()

    write_gap()

    total_row = row
    rank_row  = row + 1

    ws.row_dimensions[total_row].height = 24
    ws.row_dimensions[rank_row].height  = 24

    last_col = get_column_letter(n_inst + 1)

    for r_num, label, bg in [
        (total_row, "TOTAL POINTS", C_TOTAL_BG),
        (rank_row,  "RANKING",      C_RANK_BG),
    ]:
        lbl = ws.cell(row=r_num, column=1, value=label)
        lbl.font      = font(bold=True, size=11, color=C_WHITE)
        lbl.fill      = fill(bg)
        lbl.alignment = Alignment(horizontal="left", vertical="center", indent=1)
        for c in range(2, n_inst + 2):
            cell           = ws.cell(row=r_num, column=c)
            cell.fill      = fill(bg)
            cell.font      = font(bold=True, size=11, color=C_WHITE)
            cell.alignment = Alignment(horizontal="center", vertical="center")

    if score_rows:
        rank_range = f"$B${total_row}:${last_col}${total_row}"
        for col_idx in range(2, n_inst + 2):
            col_letter = get_column_letter(col_idx)
            parts = "+".join(f"{col_letter}{r}" for r in score_rows)
            ws.cell(row=total_row, column=col_idx, value=f"={parts}")
            ws.cell(row=rank_row,  column=col_idx,
                    value=f"=RANK({col_letter}{total_row},{rank_range},0)")

    output = BytesIO()
    wb.save(output)
    output.seek(0)

    return send_file(
        output,
        as_attachment=True,
        download_name="score_template.xlsx",
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
from datetime import datetime, timedelta, timezone
from flask import (
    Blueprint, render_template, jsonify, abort,
    send_file, redirect, url_for
)
from flask_jwt_extended import jwt_required, current_user
from functools import wraps

from App.controllers.hr import (
    get_institutions_this_year,
    get_participants_this_year,
    get_reports_count,
    get_institutions_per_year,
    get_latest_report,
    get_all_reports,
    get_report,
    create_report,
    mark_report_read,
    mark_all_reports_read,
    delete_report,
    delete_all_reports,
    build_report_data,
)

hr_views = Blueprint('hr_views', __name__, template_folder='../templates')

TRINIDAD_TZ = timezone(timedelta(hours=-4))

def _local_now():
    return datetime.now(TRINIDAD_TZ)


def hr_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        from flask_jwt_extended import verify_jwt_in_request
        verify_jwt_in_request()
        if current_user.role != "hr":
            abort(403)
        return f(*args, **kwargs)
    return decorated


# DASHBOARD
@hr_views.route("/hr/")
@hr_required
def hr_dashboard():
    season = str(_local_now().year)
    return render_template(
        "hr/hr_dashboard.html",
        current_season         = season,
        institutions_this_year = get_institutions_this_year(),
        participants_this_year = get_participants_this_year(),
        reports_count          = get_reports_count(current_user.userID),
        institutions_per_year  = get_institutions_per_year(),
        latest_report          = get_latest_report(current_user.userID),
    )
    

# REPORTS LIST
@hr_views.route("/hr/reports")
@hr_required
def hr_reports():
    reports = get_all_reports(current_user.userID)
    return render_template("hr/hr_reports.html", reports=reports)

# REPORT PREVIEW 
@hr_views.route("/hr/reports/preview")
@hr_required
def hr_report_preview():
    data = build_report_data()
    return jsonify(data)

# GENERATE REPORT 
@hr_views.route("/hr/reports/generate", methods=["POST"])
@hr_required
def hr_generate_report():
    now = _local_now()
    season = str(now.year)
    filename = f"CariFinReport_{season}_{now.strftime('%Y%m%d%H%M%S')}.pdf"
    report = create_report(
        filename=filename,
        generated_by=current_user.userID,
        season=season,
        filepath=None,
    )
    return jsonify({"success": True, "report_id": report.reportID, "filename": filename})

# DOWNLOAD REPORT 
@hr_views.route("/hr/reports/<int:report_id>/download")
@hr_required
def hr_download_report(report_id):
    import io
    report = get_report(report_id)
    if not report or report.generated_by != current_user.userID:
        abort(404)
    season = report.season or str(_local_now().year)
    data = build_report_data(season)
    pdf_bytes = _stub_pdf(data, season)
    buf = io.BytesIO(pdf_bytes)
    buf.seek(0)
    try:
        return send_file(buf, mimetype="application/pdf", as_attachment=True, download_name=report.filename)
    except TypeError:
        return send_file(buf, mimetype="application/pdf", as_attachment=True, attachment_filename=report.filename)


def _stub_pdf(data, season):
    content = (
        f"CariFin Results & Scoring System\n"
        f"Season: {season}\n"
        f"Institutions: {data['institutions_count']}\n"
        f"Participants: {data['participants_count']}\n"
        f"Generated: {_local_now().isoformat()}\n"
    )
    body = content.encode()
    pdf_txt = (
        b"%PDF-1.4\n1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj\n"
        b"2 0 obj<</Type/Pages/Kids[3 0 R]/Count 1>>endobj\n"
        b"3 0 obj<</Type/Page/MediaBox[0 0 612 792]/Parent 2 0 R"
        b"/Resources<<>>/Contents 4 0 R>>endobj\n"
        + f"4 0 obj<</Length {len(body)}>>\nstream\n".encode()
        + body
        + b"\nendstream\nendobj\n"
        b"xref\n0 5\n0000000000 65535 f\n"
        b"trailer<</Size 5/Root 1 0 R>>\n%%EOF"
    )
    return pdf_txt

# SERVE SAVED REPORT FILE 
@hr_views.route("/hr/reports/<int:report_id>/file")
@hr_required
def hr_report_file(report_id):
    report = get_report(report_id)
    if not report or report.generated_by != current_user.userID:
        abort(404)
    if not report.filepath:
        abort(404)
    return send_file(report.filepath, mimetype="application/pdf")

# MARK SINGLE REPORT AS READ 
@hr_views.route("/hr/reports/<int:report_id>/read", methods=["POST"])
@hr_required
def hr_mark_read(report_id):
    success = mark_report_read(report_id)
    return jsonify({"success": success})

# MARK ALL REPORTS AS READ 
@hr_views.route("/hr/reports/mark-all-read", methods=["POST"])
@hr_required
def hr_mark_all_read():
    mark_all_reports_read(current_user.userID)
    return jsonify({"success": True})

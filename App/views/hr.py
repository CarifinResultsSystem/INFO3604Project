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
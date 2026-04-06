from datetime import datetime, timedelta, timezone
import io
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
from App.models import AutomatedResult

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
    open_errors = AutomatedResult.query.filter_by(confirmed=False).count()
    return render_template(
        "hr/hr_dashboard.html",
        current_season         = season,
        institutions_this_year = get_institutions_this_year(),
        participants_this_year = get_participants_this_year(),
        reports_count          = get_reports_count(current_user.userID),
        institutions_per_year  = get_institutions_per_year(),
        latest_report          = get_latest_report(current_user.userID),
        open_errors            = open_errors,     # ← new
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
    data      = build_report_data(season)
    pdf_bytes = _generate_pdf(data, season)
    filename = f"CariFinReport_{season}_{now.strftime('%Y%m%d%H%M%S')}.pdf"
    report = create_report(
        filename=filename,
        generated_by=current_user.userID,
        season=season,
        filepath=None,
        pdf_data=pdf_bytes
    )
    return jsonify({"success": True, "report_id": report.reportID, "filename": filename})

# DOWNLOAD REPORT 
@hr_views.route("/hr/reports/<int:report_id>/download")
@hr_required
def hr_download_report(report_id):
    report = get_report(report_id)
    if not report or report.generated_by != current_user.userID:
        abort(404)
    
    if report.pdf_data:
        pdf_bytes = report.pdf_data
    else:
        data = build_report_data(report.season or str(_local_now().year))
        pdf_bytes = _generate_pdf(data, report.season)
    
    buf = io.BytesIO(pdf_bytes)
    buf.seek(0)
    try:
        return send_file(buf, mimetype="application/pdf", as_attachment=True, download_name=report.filename)
    except TypeError:
        return send_file(buf, mimetype="application/pdf", as_attachment=True, attachment_filename=report.filename)

def _generate_pdf(data, season):
    from reportlab.lib.pagesizes import A4
    from reportlab.lib import colors
    from reportlab.lib.units import cm
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.enums import TA_CENTER, TA_LEFT
    from reportlab.platypus import (
        SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable
    )
    import io

    PURPLE       = colors.HexColor("#4f46e5")
    PURPLE_LIGHT = colors.HexColor("#e0e7ff")
    PURPLE_MID   = colors.HexColor("#818cf8")
    DARK         = colors.HexColor("#0f0f23")
    DARK2        = colors.HexColor("#1e1b4b")
    GREY         = colors.HexColor("#6b7280")
    GREY_LIGHT   = colors.HexColor("#f3f4f6")
    GOLD         = colors.HexColor("#f59e0b")
    SILVER       = colors.HexColor("#9ca3af")
    BRONZE       = colors.HexColor("#b45309")
    WHITE        = colors.white
    GREEN        = colors.HexColor("#059669")

    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf, pagesize=A4,
        leftMargin=2*cm, rightMargin=2*cm,
        topMargin=2.5*cm, bottomMargin=2*cm,
        title=f"CariFin Report {season}",
    )

    cell_style = ParagraphStyle("Cell", fontSize=8, textColor=DARK, fontName="Helvetica", leading=11)
    cell_bold  = ParagraphStyle("CellB", fontSize=8, textColor=DARK, fontName="Helvetica-Bold", leading=11)
    body_style = ParagraphStyle("Body", fontSize=9, textColor=GREY, fontName="Helvetica", spaceAfter=4, leading=14)
    section_style = ParagraphStyle("Sec", fontSize=13, textColor=DARK, fontName="Helvetica-Bold", spaceBefore=18, spaceAfter=8)

    story = []
    now = _local_now()

    # ── Header ──
    header = Table([
        [Paragraph("CariFin Results &amp; Scoring System", ParagraphStyle("T", fontSize=24, textColor=WHITE, fontName="Helvetica-Bold", alignment=TA_CENTER))],
        [Paragraph(f"Season {season} &nbsp;·&nbsp; {now.strftime('%d %B %Y, %I:%M %p')}", ParagraphStyle("S", fontSize=10, textColor=colors.HexColor('#c4b5fd'), fontName="Helvetica", alignment=TA_CENTER))],
    ], colWidths=[17*cm])
    header.setStyle(TableStyle([
        ("BACKGROUND",    (0,0),  (-1,-1), PURPLE),
        ("TOPPADDING",    (0,0),  (-1,0),  24),
        ("BOTTOMPADDING", (0,0),  (-1,0),  14),
        ("TOPPADDING",    (0,1),  (-1,1),  10),
        ("BOTTOMPADDING", (0,1),  (-1,1),  24),
        ("ALIGN",         (0,0),  (-1,-1), "CENTER"),
    ]))
    story.append(header)
    story.append(Spacer(1, 0.5*cm))

    # Season Summary
    story.append(Spacer(1, 0.4*cm))
    story.append(Paragraph("Season Summary", section_style))
    story.append(HRFlowable(width="100%", thickness=1, color=PURPLE_LIGHT, spaceAfter=14))

    def chip(label, val):
        t = Table([
            [Paragraph(str(val), ParagraphStyle("cv", fontSize=22, fontName="Helvetica-Bold", textColor=PURPLE, alignment=TA_CENTER))],
            [Paragraph(label,    ParagraphStyle("cl", fontSize=8,  fontName="Helvetica",      textColor=GREY,   alignment=TA_CENTER))],
        ], colWidths=[5.1*cm])
        t.setStyle(TableStyle([
            ("BACKGROUND",    (0,0), (-1,-1), PURPLE_LIGHT),
            ("TOPPADDING",    (0,0), (-1,0),  16),
            ("BOTTOMPADDING", (0,0), (-1,0),  6),
            ("TOPPADDING",    (0,1), (-1,1),  4),
            ("BOTTOMPADDING", (0,1), (-1,1),  16),
            ("ALIGN",         (0,0), (-1,-1), "CENTER"),
        ]))
        return t

    stats = Table([[
        chip("Institutions",      data.get("institutions_count", 0)),
        chip("Participants",      data.get("participants_count", 0)),
        chip("Reports Generated", data.get("reports_count", 0)),
    ]], colWidths=[5.4*cm]*3, hAlign="CENTER")
    stats.setStyle(TableStyle([
        ("INNERGRID", (0,0), (-1,-1), 0.5, WHITE),
        ("BOX",       (0,0), (-1,-1), 0,   WHITE),
        ("LEFTPADDING",  (0,0), (-1,-1), 6),
        ("RIGHTPADDING", (0,0), (-1,-1), 6),
    ]))
    story.append(stats)
    story.append(Spacer(1, 0.6*cm))

    # Awards
    story.append(Paragraph("Award Results by Category", section_style))
    story.append(HRFlowable(width="100%", thickness=1, color=PURPLE_LIGHT, spaceAfter=10))
    awards = data.get("awards", [])
    if awards:
        rows = [[Paragraph(h, cell_bold) for h in ["Event","Institution","Participant","Place","Score"]]]
        for a in awards:
            p = a.get("place")
            badge = f"{'🥇 1st' if p==1 else '🥈 2nd' if p==2 else '🥉 3rd' if p==3 else str(p)}"
            bc    = GOLD if p==1 else SILVER if p==2 else BRONZE if p==3 else GREY
            rows.append([
                Paragraph(str(a.get("event_name") or "—"), cell_style),
                Paragraph(str(a.get("institution")  or "—"), cell_bold),
                Paragraph(str(a.get("participant")  or "—"), cell_style),
                Paragraph(badge, ParagraphStyle("b", fontSize=8, textColor=bc, fontName="Helvetica-Bold")),
                Paragraph(str(a.get("score") or "—"), cell_style),
            ])
        t = Table(rows, colWidths=[4.2*cm,4*cm,3.5*cm,2.2*cm,2.1*cm], repeatRows=1)
        t.setStyle(TableStyle([
            ("BACKGROUND",(0,0),(-1,0),PURPLE),("TEXTCOLOR",(0,0),(-1,0),WHITE),
            ("FONTSIZE",(0,0),(-1,-1),8),("ROWPADDING",(0,0),(-1,-1),7),
            ("ROWBACKGROUNDS",(0,1),(-1,-1),[WHITE,GREY_LIGHT]),
            ("GRID",(0,0),(-1,-1),0.4,colors.HexColor("#e5e7eb")),("VALIGN",(0,0),(-1,-1),"MIDDLE"),
        ]))
        story.append(t)
    else:
        story.append(Paragraph("No award data available yet.", body_style))

    story.append(Spacer(1, 0.4*cm))

    # Errors
    story.append(Paragraph("Automated Error Summary", section_style))
    story.append(HRFlowable(width="100%", thickness=1, color=PURPLE_LIGHT, spaceAfter=10))
    errors = data.get("error_summary", [])
    if errors:
        max_val = max((e.get("count", 0) for e in errors), default=1)
        RED_LIGHT = colors.HexColor("#fee2e2")
        GREEN_LIGHT = colors.HexColor("#dcfce7")

        rows = [[Paragraph(h, cell_bold) for h in
                ["Error Type", "Total", "Resolved", "Open", "Frequency"]]]

        for e in errors:
            total    = e.get("count", 0)
            resolved = e.get("resolved", 0)
            open_ct  = e.get("open", total)
            bar_w    = max(0.3, total / max_val * 6)

            bar = Table([[""]], colWidths=[bar_w * cm], rowHeights=[0.3 * cm])
            bar.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, -1), PURPLE_MID)]))

            open_style = ParagraphStyle(
                "open", fontSize=8, fontName="Helvetica-Bold",
                textColor=colors.HexColor("#dc2626") if open_ct > 0 else colors.HexColor("#16a34a")
            )

            rows.append([
                Paragraph(str(e.get("type") or "Unknown"), cell_style),
                Paragraph(str(total),    cell_bold),
                Paragraph(str(resolved), ParagraphStyle("res", fontSize=8, fontName="Helvetica",
                                                        textColor=colors.HexColor("#16a34a"))),
                Paragraph(str(open_ct),  open_style),
                bar,
            ])

        t = Table(rows, colWidths=[5*cm, 1.8*cm, 2*cm, 1.8*cm, 6.4*cm], repeatRows=1)
        t.setStyle(TableStyle([
            ("BACKGROUND",    (0, 0), (-1, 0),  PURPLE),
            ("TEXTCOLOR",     (0, 0), (-1, 0),  WHITE),
            ("FONTSIZE",      (0, 0), (-1, -1), 8),
            ("ROWPADDING",    (0, 0), (-1, -1), 7),
            ("ROWBACKGROUNDS",(0, 1), (-1, -1), [WHITE, GREY_LIGHT]),
            ("GRID",          (0, 0), (-1, -1), 0.4, colors.HexColor("#e5e7eb")),
            ("VALIGN",        (0, 0), (-1, -1), "MIDDLE"),
        ]))
        story.append(t)
    else:
        story.append(Paragraph("No error data available.", body_style))

    story.append(Spacer(1, 0.4*cm))

    # Paricipants
    story.append(Paragraph("Participant Directory", section_style))
    story.append(HRFlowable(width="100%", thickness=1, color=PURPLE_LIGHT, spaceAfter=10))
    participants = data.get("participants", [])
    if participants:
        rows = [[Paragraph(h, cell_bold) for h in ["Participant","Gender","DOB","Institution","Location","Events"]]]
        for p in participants:
            rows.append([
                Paragraph(f"{p.get('firstName','')} {p.get('lastName','')}", cell_bold),
                Paragraph(str(p.get("gender") or "—"),      cell_style),
                Paragraph(str(p.get("dateOfBirth") or "—"), cell_style),
                Paragraph(str(p.get("institution") or "—"), cell_style),
                Paragraph(str(p.get("location") or "—"),    cell_style),
                Paragraph(", ".join(p.get("events", [])) or "—", cell_style),
            ])
        t = Table(rows, colWidths=[3.5*cm,2*cm,2.3*cm,3.2*cm,2.5*cm,3.5*cm], repeatRows=1)
        t.setStyle(TableStyle([
            ("BACKGROUND",(0,0),(-1,0),PURPLE),("TEXTCOLOR",(0,0),(-1,0),WHITE),
            ("FONTSIZE",(0,0),(-1,-1),7.5),("ROWPADDING",(0,0),(-1,-1),6),
            ("ROWBACKGROUNDS",(0,1),(-1,-1),[WHITE,GREY_LIGHT]),
            ("GRID",(0,0),(-1,-1),0.4,colors.HexColor("#e5e7eb")),("VALIGN",(0,0),(-1,-1),"MIDDLE"),
        ]))
        story.append(t)
    else:
        story.append(Paragraph("No participants registered yet.", body_style))

    # ── Footer ──
    story.append(Spacer(1, 0.5*cm))
    story.append(HRFlowable(width="100%", thickness=0.5, color=PURPLE_LIGHT))
    story.append(Spacer(1, 0.2*cm))
    story.append(Paragraph(
        f"CariFin Results &amp; Scoring System &nbsp;·&nbsp; Confidential &nbsp;·&nbsp; {now.strftime('%d %B %Y')}",
        ParagraphStyle("foot", fontSize=7, textColor=GREY, alignment=TA_CENTER)
    ))

    doc.build(story)
    buf.seek(0)
    return buf.read()

# SERVE SAVED REPORT FILE 
@hr_views.route("/hr/reports/<int:report_id>/file")
@hr_required
def hr_report_file(report_id):
    report = get_report(report_id)
    if not report or report.generated_by != current_user.userID:
        abort(404)

    if report.pdf_data:
        pdf_bytes = report.pdf_data
    else:
        data = build_report_data(report.season or str(_local_now().year))
        pdf_bytes = _generate_pdf(data, report.season)

    buf = io.BytesIO(pdf_bytes)
    buf.seek(0)
    return send_file(buf, mimetype="application/pdf", as_attachment=False, download_name=report.filename)

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

# DELETE SINGLE REPORT
@hr_views.route("/hr/reports/<int:report_id>/delete", methods=["POST"])
@hr_required
def hr_delete_report(report_id):
    report = get_report(report_id)
    if not report or report.generated_by != current_user.userID:
        return jsonify({"success": False, "error": "Not found"}), 404
    success = delete_report(report_id)
    return jsonify({"success": success})

# DELETE ALL REPORTS
@hr_views.route("/hr/reports/delete-all", methods=["POST"])
@hr_required
def hr_delete_all():
    delete_all_reports(current_user.userID)
    return jsonify({"success": True})

# LIVE STATS POLLING
@hr_views.route("/hr/stats")
@hr_required
def hr_stats():
    open_errors = AutomatedResult.query.filter_by(confirmed=False).count()
    return jsonify({
        "institutions_this_year": get_institutions_this_year(),
        "participants_this_year": get_participants_this_year(),
        "reports_count":          get_reports_count(current_user.userID),
        "institutions_per_year":  get_institutions_per_year(),
        "open_errors":            open_errors,    # ← new
    })
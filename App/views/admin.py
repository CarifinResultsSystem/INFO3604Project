from datetime import date, timedelta

from flask import Blueprint, jsonify, render_template, redirect, url_for, flash, request
from flask_jwt_extended import jwt_required, current_user, verify_jwt_in_request
from sqlalchemy import func

from App.models import User, Event, Institution, PointsRules
from App.database import db
from App.controllers.admin import assignRole
from App.controllers.event import create_event, delete_event, update_event

admin_views = Blueprint(
    "admin_views",
    __name__,
    template_folder="../templates"
)

def admin_only():
    verify_jwt_in_request(optional=True)
    return current_user is not None and getattr(current_user, "role", None) == "admin"


@admin_views.before_request
def block_non_admins():
    if request.path.startswith("/admin"):
        verify_jwt_in_request(optional=True)
        if not admin_only():
            flash("You do not have access to this page.", "error")
            return redirect(url_for("index_views.index_page"))


@admin_views.route("/admin/")
@jwt_required()
def admin_dashboard():
    return render_template("admin/admin.html", user=current_user)


@admin_views.route("/admin/users")
@jwt_required()
def admin_users():
    users = User.query.order_by(User.userID.asc()).all()
    return render_template("admin/users.html", user=current_user, users=users)


@admin_views.route("/admin/users/<int:user_id>/role", methods=["POST"])
@jwt_required()
def admin_set_user_role(user_id):
    role = request.form.get("role", "").strip()
    updated = assignRole(user_id, role)

    if updated is None:
        flash("Could not update user role.", "error")
    else:
        flash("Role updated successfully.", "success")

    return redirect(url_for("admin_views.admin_users"))

@admin_views.route("/admin/events")
@jwt_required()
def admin_events():
    events = Event.query.order_by(Event.eventName.asc()).all()
    print("EVENT COUNT:", len(events))
    return render_template("admin/events.html", user=current_user, events=events)


@admin_views.route("/admin/events/create", methods=["POST"])
@jwt_required()
def admin_events_create():
    eventName = request.form.get("eventName", "")
    eventDate = request.form.get("eventDate", "")
    eventTime = request.form.get("eventTime", "")
    eventLocation = request.form.get("eventLocation", "")

    ev, err = create_event(eventName, eventDate, eventTime, eventLocation)
    if err:
        flash(err, "error")
    else:
        flash(f"Event created: {ev.eventName}", "success")

    return redirect(url_for("admin_views.admin_events"))


@admin_views.route("/admin/events/<int:event_id>/delete", methods=["POST"])
@jwt_required()
def admin_events_delete(event_id):
    ok = delete_event(event_id)
    flash("Event removed." if ok else "Event not found.", "success" if ok else "error")
    return redirect(url_for("admin_views.admin_events"))


@admin_views.route("/admin/events/<int:event_id>/update", methods=["POST"])
@jwt_required()
def admin_events_update(event_id):
    eventName = request.form.get("eventName", "")
    eventDate = request.form.get("eventDate", "")
    eventTime = request.form.get("eventTime", "")
    eventLocation = request.form.get("eventLocation", "")

    ev, err = update_event(event_id, eventName, eventDate, eventTime, eventLocation)
    if err:
        flash(err, "error")
    else:
        flash("Event updated.", "success")

    return redirect(url_for("admin_views.admin_events"))


@admin_views.route("/admin/institutions")
@jwt_required()
def admin_institutions():
    return render_template("admin/institutions.html", user=current_user)


@admin_views.route("/admin/awards")
@jwt_required()
def admin_awards():
    return render_template("admin/awards.html", user=current_user)


@admin_views.route("/admin/api/institutions/series")
@jwt_required()
def admin_institutions_series():
    days = int(request.args.get("days", 30))
    days = max(7, min(days, 365))

    total = db.session.query(func.count(Institution.id)).scalar() or 0

    labels = []
    values = []
    start = date.today() - timedelta(days=days - 1)

    for i in range(days):
        d = start + timedelta(days=i)
        labels.append(d.isoformat())
        values.append(int(total))

    return jsonify({"labels": labels, "values": values})

@admin_views.route("/admin/events/<int:event_id>/rules", methods=["GET"])
@jwt_required()
def admin_event_rules(event_id):
    ev = db.session.get(Event, event_id)
    if not ev:
        return jsonify({"error": "Event not found"}), 404

    rules = PointsRules.query.filter_by(eventID=event_id).all()

    individual = []
    team = []

    for r in rules:
        if r.conditionType == "placement":
            individual.append({
                "pointsID": r.pointsID,
                "placement": r.conditionValue,
                "label": r.label or "",
                "points": float(r.points),
            })
        else:
            team.append({
                "pointsID": r.pointsID,
                "conditionType": r.conditionType,
                "label": r.label or "",
                "lowerLimit": r.lowerLimit,
                "upperLimit": r.upperLimit,
                "points": float(r.points),
            })

    individual.sort(key=lambda x: x["placement"])
    return jsonify({"eventID": ev.eventID, "eventName": ev.eventName, "individual": individual, "team": team})

@admin_views.route("/admin/events/<int:event_id>/rules", methods=["POST"])
@jwt_required()
def admin_event_rules_save(event_id):
    ev = db.session.get(Event, event_id)
    if not ev:
        return jsonify({"error": "Event not found"}), 404

    payload = request.get_json(silent=True) or {}
    ind = payload.get("individual", [])
    team = payload.get("team", [])

    def update_rule(item, kind):
        rid = int(item.get("pointsID"))
        r = db.session.get(PointsRules, rid)
        if not r or getattr(r, "eventID", None) != event_id:
            return

        r.label = (item.get("label") or "").strip()
        r.points = float(item.get("points") or 0)

        if kind == "placement":
            r.conditionType = "placement"
            r.conditionValue = int(item.get("placement"))
            r.lowerLimit = None
            r.upperLimit = None
        else:
            r.conditionType = (item.get("conditionType") or "").strip()
            r.lowerLimit = int(item.get("lowerLimit") or 0)
            r.upperLimit = int(item.get("upperLimit") or 0)
            r.conditionValue = None

    for item in ind:
        update_rule(item, "placement")
    for item in team:
        update_rule(item, "team")

    db.session.commit()
    return jsonify({"success": True})
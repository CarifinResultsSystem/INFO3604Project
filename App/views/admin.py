from datetime import date, datetime, timedelta
from uuid import uuid4

from flask import Blueprint, jsonify, render_template, redirect, url_for, flash, request
from flask_jwt_extended import jwt_required, current_user, verify_jwt_in_request
from sqlalchemy.exc import IntegrityError
from sqlalchemy import func
from werkzeug.security import generate_password_hash

from App.models import User, Event, Institution, PointsRules, Participant, Season
from App.database import db
from App.controllers.admin import assignRole
from App.controllers.event import create_event, delete_event, update_event
from App.controllers.participant import create_participant 

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
    role = (request.form.get("role") or "").strip().lower()

    updated = assignRole(user_id, role)

    if updated is None:
        flash("Could not update user role.", "error")
    else:
        flash("Role updated successfully.", "success")

    return redirect(url_for("admin_views.admin_users"))

@admin_views.route("/admin/users/create", methods=["POST"])
@jwt_required()
def admin_create_user():
    username = (request.form.get("username") or "").strip()
    email = (request.form.get("email") or "").strip().lower()
    password = (request.form.get("password") or "").strip()
    role = (request.form.get("role") or "user").strip().lower()

    if not username or not email or not password:
        flash("Username, email, and password are required.", "error")
        return redirect(url_for("admin_views.admin_users"))

    if role not in User.ALLOWED_ROLES:
        flash("Invalid role selected.", "error")
        return redirect(url_for("admin_views.admin_users"))
    
    if User.query.filter_by(username=username).first():
        flash("Username already exists.", "error")
        return redirect(url_for("admin_views.admin_users"))

    if User.query.filter_by(email=email).first():
        flash("Email already exists.", "error")
        return redirect(url_for("admin_views.admin_users"))

    try:
        new_user = User(username=username, role=role, email=email, password=password)
        db.session.add(new_user)
        db.session.commit()
        flash("User created successfully.", "success")
    except ValueError as e:
        db.session.rollback()
        flash(str(e), "error")
    except IntegrityError:
        db.session.rollback()
        flash("Could not create user (username/email must be unique).", "error")

    return redirect(url_for("admin_views.admin_users"))

@admin_views.route('/admin/participants/create', methods=['POST'])
def admin_participants_create():
    try:
        participantID = str(uuid4())

        firstName = request.form.get("firstName", "").strip()
        lastName = request.form.get("lastName", "").strip()
        gender = request.form.get("gender")
        dateOfBirth = request.form.get("dateOfBirth")
        location = request.form.get("location", "").strip()
        institutionID = request.form.get("institutionID")

        # ✅ checkboxes -> list of strings
        eventIDs = request.form.getlist("eventIDs")

        create_participant(
            participantID=participantID,
            firstName=firstName,
            lastName=lastName,
            gender=gender,
            dateOfBirth=dateOfBirth,
            location=location,
            institutionID=institutionID,
            eventIDs=eventIDs
        )

        flash("Participant added.", "success")
    except Exception as e:
        flash(str(e), "error")

    return redirect(url_for("admin_views.admin_institutions"))

@admin_views.route("/admin/events")
@jwt_required()
def admin_events():
    events  = Event.query.order_by(Event.eventName.asc()).all()
    seasons = Season.query.order_by(Season.year.desc()).all()

    current_year = datetime.now().year

    # get ONLY ONE season for the current year
    current_season = Season.query.filter_by(year=current_year).first()

    return render_template(
        "admin/events.html",
        user=current_user,
        events=events,
        seasons=seasons,
        current_season_id=current_season.seasonID if current_season else None
    )


@admin_views.route("/admin/events/create", methods=["POST"])
@jwt_required()
def admin_events_create():
    eventName     = request.form.get("eventName", "").strip()
    eventDate     = request.form.get("eventDate", "")
    eventTime     = request.form.get("eventTime", "")
    eventLocation = request.form.get("eventLocation", "")
    seasonID      = request.form.get("seasonID", "")

    # Check for duplicate name within the same season
    if seasonID:
        duplicate = Event.query.filter(
            func.lower(Event.eventName) == eventName.lower(),
            Event.seasonID == int(seasonID)
        ).first()
        if duplicate:
            flash(f'An event named "{eventName}" already exists in this season.', "error")
            return redirect(url_for("admin_views.admin_events"))

    ev, err = create_event(eventName, eventDate, eventTime, eventLocation, seasonID)
    if err:
        flash(err, "error")
        return redirect(url_for("admin_views.admin_events"))

    flash(f"Event created: {ev.eventName}", "success")

    # Auto-duplicate into every future season 
    try:
        current_season = db.session.get(Season, int(seasonID))
        if not current_season or not ev.eventDate:
            return redirect(url_for("admin_views.admin_events"))

        future_seasons = Season.query.filter(
            Season.year > current_season.year
        ).order_by(Season.year.asc()).all()

        for next_season in future_seasons:
            # Skip if a same-named event already exists in that season
            already_exists = Event.query.filter(
                func.lower(Event.eventName) == eventName.lower(),
                Event.seasonID == next_season.seasonID
            ).first()
            if already_exists:
                continue

            year_diff = next_season.year - current_season.year
            try:
                next_date = ev.eventDate.replace(year=ev.eventDate.year + year_diff)
            except ValueError:
                next_date = ev.eventDate.replace(
                    year=ev.eventDate.year + year_diff, day=28
                )

            time_str = ev.time.strftime("%H:%M") if ev.time else "00:00"
            dup, dup_err = create_event(
                ev.eventName,
                next_date.isoformat(),
                time_str,
                ev.location or "",
                str(next_season.seasonID)
            )
            if dup_err:
                flash(f"Could not duplicate into season {next_season.year}: {dup_err}", "error")
            else:
                flash(f"Duplicated into season {next_season.year}.", "success")

    except Exception as e:
        flash(f"Duplication error: {str(e)}", "error")

    return redirect(url_for("admin_views.admin_events"))


@admin_views.route("/admin/seasons/create", methods=["POST"])
@jwt_required()
def admin_seasons_create():
    year = request.form.get("seasonYear", "").strip()
    if not year or not year.isdigit():
        flash("A valid year is required.", "error")
        return redirect(url_for("admin_views.admin_events"))
    if Season.query.filter_by(year=int(year)).first():
        flash(f"Season {year} already exists.", "error")
        return redirect(url_for("admin_views.admin_events"))
    try:
        s = Season(year=int(year))
        db.session.add(s)
        db.session.commit()
        flash(f"Season {year} created.", "success")
    except Exception as e:
        db.session.rollback()
        flash(str(e), "error")
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
    eventName     = request.form.get("eventName", "")
    eventDate     = request.form.get("eventDate", "")
    eventTime     = request.form.get("eventTime", "")
    eventLocation = request.form.get("eventLocation", "")
    seasonID      = request.form.get("seasonID", "")

    ev, err = update_event(event_id, eventName, eventDate, eventTime, eventLocation, seasonID)
    if err:
        flash(err, "error")
    else:
        flash("Event updated.", "success")

    return redirect(url_for("admin_views.admin_events"))


@admin_views.route("/admin/institutions", methods=["GET", "POST"])
@jwt_required()
def admin_institutions():
    if request.method == "POST":
        name = (request.form.get("institutionName") or "").strip()
        loc  = (request.form.get("institutionLocation") or "").strip()

        if not name or not loc:
            flash("Institution name and location required.", "error")
            return redirect(url_for("admin_views.admin_institutions"))

        inst = Institution(name, loc)
        
        try:
            db.session.add(inst)
            db.session.commit()

            flash("Institution added successfully.", "success")
            return redirect(url_for("admin_views.admin_institutions"))

            inst = Institution(name, loc)
            inst.insName = name
            inst.insLocation = loc

        except IntegrityError:
            db.session.rollback()
            flash("Could not add institution (maybe it already exists).", "error")

        return redirect(url_for("admin_views.admin_institutions"))

    institutions = Institution.query.order_by(Institution.insName.asc()).all()
    events = Event.query.order_by(Event.eventName.asc()).all()

    return render_template(
        "admin/institutions.html",
        user=current_user,
        institutions=institutions,
        events=events,
        participants=Participant.query.all(),
        total_institutions=len(institutions),
        total_participants=Participant.query.count(),
    )


@admin_views.route("/admin/awards")
@jwt_required()
def admin_awards():
    return render_template("admin/awards.html", user=current_user)


@admin_views.route("/admin/api/institutions/series")
@jwt_required()
def admin_institutions_series():
    days = int(request.args.get("days", 30))
    days = max(7, min(days, 365))

    total = db.session.query(func.count(Institution.institutionID)).scalar() or 0

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
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
from App.controllers.hr import get_institutions_per_year

admin_views = Blueprint("admin_views", __name__, template_folder="../templates")

# ── Routes that use fetch() or plain form POST without JWT headers ──────────
# These are exempt from the jwt_required decorator but still behind before_request.
_EXEMPT_SUFFIXES = (
    "/update",
    "/delete",
    "/create",
)


def _is_admin():
    """Return True if the current request carries a valid admin JWT."""
    try:
        verify_jwt_in_request(optional=True)
    except Exception:
        return False
    return current_user is not None and getattr(current_user, "role", None) == "admin"


@admin_views.before_request
def block_non_admins():
    if not request.path.startswith("/admin"):
        return
    # Allow update/delete/create routes through — they have no JWT from fetch()
    if any(request.path.endswith(suffix) for suffix in _EXEMPT_SUFFIXES):
        return
    if _is_admin():
        return
    flash("You do not have access to this page.", "error")
    return redirect(url_for("index_views.index_page"))


# ══════════════════════════════════════════════════════════════════
#  DASHBOARD
# ══════════════════════════════════════════════════════════════════

@admin_views.route("/admin/")
@jwt_required()
def admin_dashboard():
    events = Event.query.order_by(Event.eventDate.asc(), Event.time.asc()).all()
    return render_template(
        "admin/admin.html",
        user=current_user,
        events=events,
        institutions_per_year=get_institutions_per_year(),
    )


# ══════════════════════════════════════════════════════════════════
#  USERS
# ══════════════════════════════════════════════════════════════════

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
    flash("Role updated successfully." if updated else "Could not update user role.",
          "success" if updated else "error")
    return redirect(url_for("admin_views.admin_users"))


@admin_views.route("/admin/users/create", methods=["POST"])
@jwt_required()
def admin_create_user():
    username = (request.form.get("username") or "").strip()
    email    = (request.form.get("email")    or "").strip().lower()
    password = (request.form.get("password") or "").strip()
    role     = (request.form.get("role")     or "user").strip().lower()

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
        db.session.add(User(username=username, role=role, email=email, password=password))
        db.session.commit()
        flash("User created successfully.", "success")
    except (ValueError, IntegrityError) as exc:
        db.session.rollback()
        flash(str(exc), "error")
    return redirect(url_for("admin_views.admin_users"))


# ══════════════════════════════════════════════════════════════════
#  EVENTS
# ══════════════════════════════════════════════════════════════════

@admin_views.route("/admin/events")
@jwt_required()
def admin_events():
    from App.models.challenge import Challenge
    events        = Event.query.order_by(Event.eventName.asc()).all()
    seasons       = Season.query.order_by(Season.year.desc()).all()
    challenges    = Challenge.query.order_by(Challenge.challengeName.asc()).all()
    current_year  = datetime.now().year
    current_season = Season.query.filter_by(year=current_year).first()
    return render_template(
        "admin/events.html",
        user=current_user,
        events=events,
        seasons=seasons,
        challenges=challenges,
        current_season_id=current_season.seasonID if current_season else None,
    )


@admin_views.route("/admin/events/create", methods=["POST"])
@jwt_required()
def admin_events_create():
    import json as _json

    eventName     = request.form.get("eventName", "").strip()
    eventDate     = request.form.get("eventDate", "")
    eventTime     = request.form.get("eventTime", "")
    eventLocation = request.form.get("eventLocation", "")
    seasonID      = request.form.get("seasonID", "")

    if seasonID:
        duplicate = Event.query.filter(
            func.lower(Event.eventName) == eventName.lower(),
            Event.seasonID == int(seasonID),
        ).first()
        if duplicate:
            flash(f'An event named "{eventName}" already exists in this season.', "error")
            return redirect(url_for("admin_views.admin_events"))

    ev, err = create_event(eventName, eventDate, eventTime, eventLocation, seasonID)
    if err:
        flash(err, "error")
        return redirect(url_for("admin_views.admin_events"))

    try:
        ind_rules  = _json.loads(request.form.get("rulesIndividual", "[]") or "[]")
        team_rules = _json.loads(request.form.get("rulesTeam",       "[]") or "[]")

        for item in ind_rules:
            db.session.add(PointsRules(
                eventID=ev.eventID, seasonID=ev.seasonID, ruleType="individual",
                placement=int(item.get("placement", 0)),
                label=(item.get("label") or "").strip(),
                points=float(item.get("points") or 0),
            ))
        for item in team_rules:
            db.session.add(PointsRules(
                eventID=ev.eventID, seasonID=ev.seasonID, ruleType="team",
                category=(item.get("conditionType") or "").strip(),
                label=(item.get("label") or "").strip(),
                points=float(item.get("points") or 0),
            ))
        if ind_rules or team_rules:
            db.session.commit()
    except Exception as exc:
        db.session.rollback()
        flash(f"Event created but rules could not be saved: {exc}", "error")
        return redirect(url_for("admin_views.admin_events"))

    flash(f"Event created: {ev.eventName}", "success")
    return redirect(url_for("admin_views.admin_events"))


@admin_views.route("/admin/events/duplicate-season", methods=["POST"])
@jwt_required()
def admin_events_duplicate_season():
    source_id = request.form.get("sourceSeasonID", "").strip()
    target_id = request.form.get("targetSeasonID", "").strip()

    if not source_id or not target_id:
        flash("Both a source and target season are required.", "error")
        return redirect(url_for("admin_views.admin_events"))
    if source_id == target_id:
        flash("Source and target seasons must be different.", "error")
        return redirect(url_for("admin_views.admin_events"))

    source = db.session.get(Season, int(source_id))
    target = db.session.get(Season, int(target_id))
    if not source or not target:
        flash("Invalid season selection.", "error")
        return redirect(url_for("admin_views.admin_events"))

    source_events = Event.query.filter_by(seasonID=source.seasonID).all()
    if not source_events:
        flash(f"No events found in season {source.year} to duplicate.", "error")
        return redirect(url_for("admin_views.admin_events"))

    year_diff = target.year - source.year
    created = skipped = 0

    for ev in source_events:
        if Event.query.filter(
            func.lower(Event.eventName) == ev.eventName.lower(),
            Event.seasonID == target.seasonID,
        ).first():
            skipped += 1
            continue

        next_date = None
        if ev.eventDate:
            try:
                next_date = ev.eventDate.replace(year=ev.eventDate.year + year_diff)
            except ValueError:
                next_date = ev.eventDate.replace(year=ev.eventDate.year + year_diff, day=28)

        _, err = create_event(
            ev.eventName,
            next_date.isoformat() if next_date else "",
            ev.time.strftime("%H:%M") if ev.time else "00:00",
            ev.location or "",
            str(target.seasonID),
        )
        if err:
            flash(f'Could not duplicate "{ev.eventName}": {err}', "error")
        else:
            created += 1

    parts = []
    if created:
        parts.append(f"{created} event{'s' if created != 1 else ''} duplicated into season {target.year}")
    if skipped:
        parts.append(f"{skipped} skipped (already exist)")
    flash(". ".join(parts) + ".", "success" if created else "error")
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
        db.session.add(Season(year=int(year)))
        db.session.commit()
        flash(f"Season {year} created.", "success")
    except Exception as exc:
        db.session.rollback()
        flash(str(exc), "error")
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
    eventName     = request.form.get("eventName", "").strip()
    eventDate     = request.form.get("eventDate", "").strip()
    eventTime     = request.form.get("eventTime", "").strip()
    eventLocation = request.form.get("eventLocation", "").strip()
    seasonID      = request.form.get("seasonID", "").strip()

    if not seasonID:
        existing = db.session.get(Event, event_id)
        if existing and existing.seasonID:
            seasonID = str(existing.seasonID)

    ev, err = update_event(event_id, eventName, eventDate, eventTime, eventLocation, seasonID)
    if err:
        return jsonify({"success": False, "error": err}), 400
    return jsonify({"success": True})


# ══════════════════════════════════════════════════════════════════
#  INSTITUTIONS & PARTICIPANTS
# ══════════════════════════════════════════════════════════════════

def _institutions_page_data():
    institutions = Institution.query.order_by(Institution.insName.asc()).all()
    return dict(
        user=current_user,
        institutions=institutions,
        events=Event.query.order_by(Event.eventName.asc()).all(),
        seasons=Season.query.order_by(Season.year.asc()).all(),
        participants=Participant.query.all(),
        total_institutions=len(institutions),
        total_participants=Participant.query.count(),
    )


@admin_views.route("/admin/institutions", methods=["GET", "POST"])
@jwt_required()
def admin_institutions():
    if request.method == "POST":
        name = (request.form.get("institutionName") or "").strip()
        loc  = (request.form.get("institutionLocation") or "").strip()
        if not name or not loc:
            flash("Institution name and location required.", "error")
            return redirect(url_for("admin_views.admin_institutions"))
        try:
            db.session.add(Institution(name, loc))
            db.session.commit()
            flash("Institution added successfully.", "success")
        except IntegrityError:
            db.session.rollback()
            flash("Could not add institution (maybe it already exists).", "error")
        return redirect(url_for("admin_views.admin_institutions"))

    return render_template("admin/institutions.html", **_institutions_page_data())


# ── Institution actions (no @jwt_required — browser form/fetch don't send JWT) ──

@admin_views.route("/admin/institutions/<int:institution_id>/update", methods=["POST"])
def admin_institution_update(institution_id):
    inst = db.session.get(Institution, institution_id)
    if not inst:
        return jsonify({"success": False, "error": "Institution not found"}), 404
    name = (request.form.get("insName") or "").strip()
    loc  = (request.form.get("insLocation") or "").strip()
    if not name or not loc:
        return jsonify({"success": False, "error": "Name and location are required"}), 400
    inst.insName     = name
    inst.insLocation = loc
    try:
        db.session.commit()
        return jsonify({"success": True, "insName": inst.insName, "insLocation": inst.insLocation})
    except Exception as exc:
        db.session.rollback()
        return jsonify({"success": False, "error": str(exc)}), 500


@admin_views.route("/admin/institutions/<int:institution_id>/delete", methods=["POST"])
def admin_institution_delete(institution_id):
    inst = db.session.get(Institution, institution_id)
    if not inst:
        flash("Institution not found.", "error")
        return redirect(url_for("admin_views.admin_institutions"))
    try:
        db.session.delete(inst)
        db.session.commit()
        flash("Institution deleted.", "success")
    except Exception as exc:
        db.session.rollback()
        flash(f"Could not delete institution: {exc}", "error")
    return redirect(url_for("admin_views.admin_institutions"))


# ── Participant actions ──────────────────────────────────────────

@admin_views.route("/admin/participants/create", methods=["POST"])
def admin_participants_create():
    try:
        create_participant(
            participantID=str(uuid4()),
            firstName=request.form.get("firstName", "").strip(),
            lastName=request.form.get("lastName",  "").strip(),
            gender=request.form.get("gender"),
            dateOfBirth=request.form.get("dateOfBirth"),
            location=request.form.get("location", "").strip(),
            institutionID=request.form.get("institutionID"),
            eventIDs=request.form.getlist("eventIDs"),
        )
        flash("Participant added.", "success")
    except Exception as exc:
        flash(str(exc), "error")
    return redirect(url_for("admin_views.admin_institutions"))


@admin_views.route("/admin/participants/<string:participant_id>/update", methods=["POST"])
def admin_participant_update(participant_id):
    p = db.session.get(Participant, participant_id)
    if not p:
        return jsonify({"success": False, "error": "Participant not found"}), 404

    p.firstName     = (request.form.get("firstName") or "").strip() or p.firstName
    p.lastName      = (request.form.get("lastName")  or "").strip() or p.lastName
    p.gender        = request.form.get("gender")        or p.gender
    p.location      = (request.form.get("location")  or "").strip() or p.location
    p.institutionID = request.form.get("institutionID") or p.institutionID

    dob = request.form.get("dateOfBirth")
    if dob:
        try:
            from datetime import date as _date
            p.dateOfBirth = _date.fromisoformat(dob)
        except ValueError:
            pass

    try:
        db.session.commit()
        return jsonify({"success": True})
    except Exception as exc:
        db.session.rollback()
        return jsonify({"success": False, "error": str(exc)}), 500


@admin_views.route("/admin/participants/<string:participant_id>/delete", methods=["POST"])
def admin_participant_delete(participant_id):
    p = db.session.get(Participant, participant_id)
    if not p:
        flash("Participant not found.", "error")
        return redirect(url_for("admin_views.admin_institutions"))
    try:
        db.session.delete(p)
        db.session.commit()
        flash("Participant deleted.", "success")
    except Exception as exc:
        db.session.rollback()
        flash(f"Could not delete participant: {exc}", "error")
    return redirect(url_for("admin_views.admin_institutions"))


# ══════════════════════════════════════════════════════════════════
#  AWARDS
# ══════════════════════════════════════════════════════════════════

@admin_views.route("/admin/awards")
@jwt_required()
def admin_awards():
    return render_template("admin/awards.html", user=current_user)


# ══════════════════════════════════════════════════════════════════
#  INSTITUTIONS CHART API
# ══════════════════════════════════════════════════════════════════

@admin_views.route("/admin/api/institutions/series")
@jwt_required()
def admin_institutions_series():
    days  = max(7, min(int(request.args.get("days", 30)), 365))
    total = db.session.query(func.count(Institution.institutionID)).scalar() or 0
    start = date.today() - timedelta(days=days - 1)
    labels = [(start + timedelta(days=i)).isoformat() for i in range(days)]
    values = [int(total)] * days
    return jsonify({"labels": labels, "values": values})


# ══════════════════════════════════════════════════════════════════
#  EVENT POINTS RULES
# ══════════════════════════════════════════════════════════════════

@admin_views.route("/admin/events/<int:event_id>/rules", methods=["GET"])
@jwt_required()
def admin_event_rules(event_id):
    ev = db.session.get(Event, event_id)
    if not ev:
        return jsonify({"error": "Event not found"}), 404

    rules = PointsRules.query.filter_by(eventID=event_id).all()
    individual, team_map, team_order = [], {}, []

    for r in rules:
        if r.ruleType == "individual":
            individual.append({
                "pointsID": r.pointsID, "placement": r.placement,
                "label": r.label or "", "points": float(r.points),
            })
        else:
            cat = r.category or "Uncategorised"
            if cat not in team_map:
                team_map[cat] = []
                team_order.append(cat)
            team_map[cat].append({
                "pointsID": r.pointsID, "conditionType": cat,
                "label": r.label or "", "points": float(r.points),
            })

    individual.sort(key=lambda x: x["placement"] or 0)
    team = [item for cat in team_order for item in team_map[cat]]

    return jsonify({"eventID": ev.eventID, "eventName": ev.eventName,
                    "individual": individual, "team": team})


@admin_views.route("/admin/events/<int:event_id>/rules", methods=["POST"])
@jwt_required()
def admin_event_rules_save(event_id):
    ev = db.session.get(Event, event_id)
    if not ev:
        return jsonify({"error": "Event not found"}), 404

    payload = request.get_json(silent=True) or {}
    try:
        for item in payload.get("individual", []):
            rid = item.get("pointsID")
            if rid:
                r = db.session.get(PointsRules, int(rid))
                if not r or r.eventID != event_id:
                    continue
                r.placement = int(item.get("placement", 0))
                r.label     = (item.get("label") or "").strip()
                r.points    = float(item.get("points") or 0)
            else:
                db.session.add(PointsRules(
                    eventID=event_id, seasonID=ev.seasonID, ruleType="individual",
                    placement=int(item.get("placement", 0)),
                    label=(item.get("label") or "").strip(),
                    points=float(item.get("points") or 0),
                ))

        for item in payload.get("team", []):
            rid = item.get("pointsID")
            if rid:
                r = db.session.get(PointsRules, int(rid))
                if not r or r.eventID != event_id:
                    continue
                r.category = (item.get("conditionType") or "").strip()
                r.label    = (item.get("label") or "").strip()
                r.points   = float(item.get("points") or 0)
            else:
                db.session.add(PointsRules(
                    eventID=event_id, seasonID=ev.seasonID, ruleType="team",
                    category=(item.get("conditionType") or "").strip(),
                    label=(item.get("label") or "").strip(),
                    points=float(item.get("points") or 0),
                ))

        db.session.commit()
        return jsonify({"success": True})
    except Exception as exc:
        db.session.rollback()
        return jsonify({"success": False, "error": str(exc)}), 500


# ══════════════════════════════════════════════════════════════════
#  CHALLENGES
# ══════════════════════════════════════════════════════════════════

@admin_views.route("/admin/challenges")
@jwt_required()
def admin_challenges():
    from App.models.challenge import Challenge
    challenges    = Challenge.query.order_by(Challenge.challengeName.asc()).all()
    events        = Event.query.order_by(Event.eventName.asc()).all()
    seasons       = Season.query.order_by(Season.year.desc()).all()
    current_year  = datetime.now().year
    current_season = Season.query.filter_by(year=current_year).first()
    return render_template(
        "admin/challenges.html",
        user=current_user,
        challenges=challenges,
        events=events,
        seasons=seasons,
        current_season_id=current_season.seasonID if current_season else None,
    )


@admin_views.route("/admin/challenges/create", methods=["POST"])
@jwt_required()
def admin_challenges_create():
    import json as _json
    from App.controllers.challenge import create_challenge, save_challenge_rules

    ch, err = create_challenge(
        challengeName=request.form.get("challengeName", "").strip(),
        seasonID=request.form.get("seasonID", "") or None,
        description=request.form.get("description", "").strip() or None,
        bonusPoints=request.form.get("bonusPoints", "0"),
        eventIDs=request.form.getlist("eventIDs"),
    )
    if err:
        flash(err, "error")
        return redirect(url_for("admin_views.admin_challenges"))

    try:
        rules_raw = request.form.get("placementRulesJSON", "[]")
        placement_rules = _json.loads(rules_raw) if rules_raw else []
        if placement_rules:
            ok, rule_err = save_challenge_rules(ch.challengeID, {"individual": placement_rules})
            if not ok:
                flash(f"Challenge created but rules could not be saved: {rule_err}", "error")
                return redirect(url_for("admin_views.admin_challenges"))
    except Exception as exc:
        flash(f"Challenge created but rules could not be saved: {exc}", "error")
        return redirect(url_for("admin_views.admin_challenges"))

    flash(f'Challenge "{ch.challengeName}" created.', "success")
    return redirect(url_for("admin_views.admin_challenges"))


@admin_views.route("/admin/challenges/<int:challenge_id>/delete", methods=["POST"])
@jwt_required()
def admin_challenges_delete(challenge_id):
    from App.controllers.challenge import delete_challenge
    ok = delete_challenge(challenge_id)
    flash("Challenge removed." if ok else "Challenge not found.", "success" if ok else "error")
    return redirect(url_for("admin_views.admin_challenges"))


@admin_views.route("/admin/challenges/<int:challenge_id>/update", methods=["POST"])
@jwt_required()
def admin_challenges_update(challenge_id):
    from App.controllers.challenge import update_challenge
    ch, err = update_challenge(
        challengeID=challenge_id,
        challengeName=request.form.get("challengeName", "").strip() or None,
        description=request.form.get("description", "").strip() or None,
        bonusPoints=request.form.get("bonusPoints") or None,
        seasonID=request.form.get("seasonID") or None,
        eventIDs=request.form.getlist("eventIDs"),
    )
    if err:
        return jsonify({"success": False, "error": err}), 400
    return jsonify({"success": True, "challengeName": ch.challengeName})


@admin_views.route("/admin/challenges/<int:challenge_id>/rules", methods=["GET"])
@jwt_required()
def admin_challenge_rules(challenge_id):
    from App.models.challenge import Challenge
    from App.controllers.challenge import get_challenge_rules
    ch = db.session.get(Challenge, challenge_id)
    if not ch:
        return jsonify({"error": "Challenge not found"}), 404
    data = get_challenge_rules(challenge_id)
    data["challengeID"]   = ch.challengeID
    data["challengeName"] = ch.challengeName
    return jsonify(data)


@admin_views.route("/admin/challenges/<int:challenge_id>/rules", methods=["POST"])
@jwt_required()
def admin_challenge_rules_save(challenge_id):
    from App.controllers.challenge import save_challenge_rules
    payload = request.get_json(silent=True) or {}
    ok, err = save_challenge_rules(challenge_id, payload)
    if not ok:
        return jsonify({"success": False, "error": err}), 500
    return jsonify({"success": True})


@admin_views.route("/admin/challenges/<int:challenge_id>/rules/<int:rule_id>/delete",
                   methods=["POST"])
@jwt_required()
def admin_challenge_rule_delete(challenge_id, rule_id):
    from App.controllers.challenge import delete_challenge_rule
    ok = delete_challenge_rule(rule_id, challenge_id)
    return jsonify({"success": ok})
from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_jwt_extended import jwt_required, current_user, verify_jwt_in_request

from App.models import User, Event
from App.database import db
from App.controllers.admin import assignRole, createEvent

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
    events = Event.query.order_by(Event.id.desc()).all()
    return render_template("admin/events.html", user=current_user, events=events)


@admin_views.route("/admin/events/create", methods=["POST"])
@jwt_required()
def admin_create_event():
    eventName = request.form.get("eventName", "").strip()
    eventDate = request.form.get("eventDate")  # may be string; depends on your model
    eventTime = request.form.get("eventTime")
    eventLocation = request.form.get("eventLocation", "").strip()

    event = createEvent(eventName, eventDate, eventTime, eventLocation)
    if event is None:
        flash("Could not create event. Check inputs.", "error")
    else:
        flash("Event created.", "success")

    return redirect(url_for("admin_views.admin_events"))


# Wireframe placeholders you can build out next:
@admin_views.route("/admin/institutions")
@jwt_required()
def admin_institutions():
    return render_template("admin/institutions.html", user=current_user)


@admin_views.route("/admin/awards")
@jwt_required()
def admin_awards():
    return render_template("admin/awards.html", user=current_user)
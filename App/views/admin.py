# App/views/admin.py
from flask import Blueprint, render_template, flash, redirect, url_for, request
from flask_jwt_extended import jwt_required, current_user
from flask_admin import Admin
from flask_admin.contrib.sqla import ModelView
from App.database import db
from App.models import User

# --- Blueprint for custom admin pages ---
admin_views = Blueprint('admin_views', __name__, template_folder='../templates/admin')

@admin_views.route('/admin/')
@jwt_required()
def admin_dashboard():
    if current_user.role != "admin":
        flash("You do not have access to this page", "error")
        return redirect(url_for("index_views.index_page"))
    return render_template('admin/admin.html', user=current_user)

# --- Flask-Admin setup ---
class AdminView(ModelView):
    @jwt_required()
    def is_accessible(self):
        return current_user is not None and current_user.role == "admin"

    def inaccessible_callback(self, name, **kwargs):
        flash("Login to access admin")
        return redirect(url_for('auth_views.login_page', next=request.url))

def setup_admin(app):
    admin = Admin(app, name='Carifin')
    admin.add_view(AdminView(User, db.session))
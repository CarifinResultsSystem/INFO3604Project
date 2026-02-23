from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, current_user  # type: ignore

from App.database import db
from App.models.season import Season

season_bp = Blueprint("season_bp", __name__)


def _require_admin():
    role = (getattr(current_user, "role", "") or "").lower().strip()
    return role == "admin"


# -------------------------
# Create Season
# -------------------------
@season_bp.route("/seasons", methods=["POST"])
@jwt_required()
def create_season():
    if not _require_admin():
        return jsonify({"error": "Admin access required"}), 403

    data = request.get_json()
    year = data.get("year")

    if not year:
        return jsonify({"error": "Year is required"}), 400

    if Season.get_by_year(year):
        return jsonify({"error": "Season already exists"}), 400

    season = Season(year=year)
    db.session.add(season)
    db.session.commit()

    return jsonify({"message": "Season created", "season": season.get_json()}), 201


# -------------------------
# Get All Seasons
# -------------------------
@season_bp.route("/seasons", methods=["GET"])
def get_all_seasons():
    seasons = Season.get_all()
    return jsonify([s.get_json() for s in seasons]), 200


# -------------------------
# Get Season by ID
# -------------------------
@season_bp.route("/seasons/<int:season_id>", methods=["GET"])
def get_season(season_id):
    season = Season.get_by_id(season_id)

    if not season:
        return jsonify({"error": "Season not found"}), 404

    return jsonify(season.get_json()), 200


# -------------------------
# Update Season
# -------------------------
@season_bp.route("/seasons/<int:season_id>", methods=["PUT"])
@jwt_required()
def update_season(season_id):
    if not _require_admin():
        return jsonify({"error": "Admin access required"}), 403

    season = Season.get_by_id(season_id)
    if not season:
        return jsonify({"error": "Season not found"}), 404

    data = request.get_json()
    new_year = data.get("year")

    if new_year:
        season.year = new_year

    db.session.commit()

    return jsonify({"message": "Season updated", "season": season.get_json()}), 200


# -------------------------
# Delete Season
# -------------------------
@season_bp.route("/seasons/<int:season_id>", methods=["DELETE"])
@jwt_required()
def delete_season(season_id):
    if not _require_admin():
        return jsonify({"error": "Admin access required"}), 403

    season = Season.get_by_id(season_id)
    if not season:
        return jsonify({"error": "Season not found"}), 404

    db.session.delete(season)
    db.session.commit()

    return jsonify({"message": "Season deleted"}), 200
import os
from flask import Blueprint, request, jsonify, current_app, send_from_directory
from flask_jwt_extended import jwt_required, current_user  # type: ignore

from App.database import db
from App.models.scoretaker import Scoretaker, ScoreDocument

scoretaker_bp = Blueprint("scoretaker_bp", __name__)


def _require_scoretaker_role() -> bool:
    """
    Enforce role == 'scoretaker'
    Assumes current_user has .role and .userID (like your UML/User model).
    """
    role = (getattr(current_user, "role", "") or "").lower().strip()
    return role == "scoretaker"


def _upload_folder() -> str:
    """
    Configurable upload folder:
      app.config["SCOREDOC_UPLOAD_FOLDER"] = "/abs/path/or/relative"
    Default:
      <app_root>/uploads/score_documents
    """
    folder = current_app.config.get("SCOREDOC_UPLOAD_FOLDER")
    if folder:
        # allow relative folder path too
        if not os.path.isabs(folder):
            return os.path.join(current_app.root_path, folder)
        return folder

    return os.path.join(current_app.root_path, "uploads", "score_documents")


@scoretaker_bp.route("/scoretaker/score-documents", methods=["POST"])
@jwt_required()
def upload_score_document():
    """
    POST /scoretaker/score-documents
    Form-data:
      file=<uploaded file>
    """
    if not _require_scoretaker_role():
        return jsonify({"error": "Forbidden (scoretaker role required)."}), 403

    if "file" not in request.files:
        return jsonify({"error": "Missing file field named 'file'."}), 400

    file_storage = request.files["file"]

    try:
        # Ensure scoretaker profile exists
        st = Scoretaker.get_or_create_for_user(current_user.userID)

        # Save file + create ScoreDocument row
        doc = st.upload_score_document(
            file_storage=file_storage,
            upload_folder=_upload_folder(),
        )

        db.session.commit()
        return jsonify({"message": "Uploaded", "document": doc.get_json()}), 201

    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 400


@scoretaker_bp.route("/scoretaker/score-documents", methods=["GET"])
@jwt_required()
def list_my_score_documents():
    """
    GET /scoretaker/score-documents
    Lists documents uploaded by the logged-in scoretaker.
    """
    if not _require_scoretaker_role():
        return jsonify({"error": "Forbidden (scoretaker role required)."}), 403

    st = db.session.get(Scoretaker, current_user.userID)
    if st is None:
        return jsonify({"documents": []}), 200

    docs = [d.get_json() for d in st.score_documents]
    return jsonify({"documents": docs}), 200


@scoretaker_bp.route("/scoretaker/score-documents/<int:document_id>", methods=["DELETE"])
@jwt_required()
def delete_score_document(document_id: int):
    """
    DELETE /scoretaker/score-documents/<document_id>
    Deletes the DB record and tries to delete the file from disk.
    """
    if not _require_scoretaker_role():
        return jsonify({"error": "Forbidden (scoretaker role required)."}), 403

    doc = db.session.get(ScoreDocument, document_id)
    if doc is None:
        return jsonify({"error": "Not found"}), 404

    if doc.scoretakerID != current_user.userID:
        return jsonify({"error": "Forbidden"}), 403

    try:
        # attempt file delete (best-effort)
        try:
            if doc.storedPath and os.path.exists(doc.storedPath):
                os.remove(doc.storedPath)
        except Exception:
            # don't fail the request if filesystem delete fails
            pass

        db.session.delete(doc)
        db.session.commit()
        return jsonify({"message": "Deleted"}), 200

    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 400


@scoretaker_bp.route("/scoretaker/score-documents/<int:document_id>/download", methods=["GET"])
@jwt_required()
def download_score_document(document_id: int):
    """
    GET /scoretaker/score-documents/<document_id>/download
    Allows the owner to download their uploaded file.
    """
    if not _require_scoretaker_role():
        return jsonify({"error": "Forbidden (scoretaker role required)."}), 403

    doc = db.session.get(ScoreDocument, document_id)
    if doc is None:
        return jsonify({"error": "Not found"}), 404

    if doc.scoretakerID != current_user.userID:
        return jsonify({"error": "Forbidden"}), 403

    directory = os.path.dirname(doc.storedPath)
    filename = os.path.basename(doc.storedPath)

    return send_from_directory(
        directory,
        filename,
        as_attachment=True,
        download_name=doc.originalFilename,
    )
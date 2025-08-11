from . import bp
from flask import request, jsonify, render_template
from app import models
import sqlite3

# Admin page at: /trp-admin
@bp.route("/", methods=["GET"])
def trp_admin_page():
    return render_template("trp_admin.html")

# Optional old input form at: /trp-admin/input
@bp.route("/input", methods=["GET"])
def contacts():
    return render_template("contacts.html")

# API
@bp.route("/trp", methods=["POST"])
def create_trp():
    data = request.get_json(force=True)
    required = ["owner", "target_group", "primary_label", "price_per_sec_eur"]
    missing = [k for k in required if not data.get(k)]
    if missing:
        return jsonify({"status": "error", "message": f"Missing: {', '.join(missing)}"}), 400
    try:
        models.upsert_trp_rate(**data)
    except ValueError as e:
        return jsonify({"status": "error", "message": str(e)}), 400
    return jsonify({"status": "ok"}), 201

@bp.route("/trp", methods=["GET"])
def list_trp():
    owner = request.args.get("owner")
    return jsonify(models.list_trp_rates(owner))

@bp.route("/trp/<int:row_id>", methods=["PATCH"])
def update_trp(row_id):
    data = request.get_json(force=True)
    try:
        models.update_trp_rate_by_id(row_id, data)
        return jsonify({"status": "ok"})
    except sqlite3.IntegrityError:
        return jsonify({"status": "error", "message": "Owner + target group already exists"}), 409
    except ValueError as e:
        return jsonify({"status": "error", "message": str(e)}), 400

@bp.route("/trp/<int:row_id>", methods=["DELETE"])
def delete_trp(row_id):
    models.delete_trp_rate(row_id)
    return jsonify({"status": "ok"})

# app/indices/routes.py
from . import bp
from flask import render_template, request, jsonify
from app import models

# ---------- Page ----------
@bp.route("/indices", methods=["GET"])
def indices_page():
    return render_template("indices_admin.html")

# ---------- Target Groups API ----------
@bp.route("/target-groups", methods=["GET"])
def target_groups_list():
    """Get all available target groups"""
    return jsonify(models.get_target_groups_list())

# ---------- Duration Indices API ----------
@bp.route("/duration-indices", methods=["GET"])
def duration_indices_list():
    """Get all duration indices grouped by target group"""
    return jsonify(models.list_duration_indices())

@bp.route("/duration-indices", methods=["POST"])
def duration_indices_create():
    """Create or update duration index"""
    data = request.get_json(force=True)
    target_group = data.get("target_group")
    duration = data.get("duration_seconds")
    index_value = data.get("index_value")
    description = data.get("description", "")
    
    if not target_group or duration is None or index_value is None:
        return jsonify({"status": "error", "message": "target_group, duration_seconds and index_value required"}), 400
    
    try:
        models.update_duration_index(target_group, int(duration), float(index_value), description.strip() or None)
        return jsonify({"status": "ok"}), 201
    except ValueError as e:
        return jsonify({"status": "error", "message": str(e)}), 400

@bp.route("/duration-indices/<target_group>/<int:duration_seconds>", methods=["DELETE"])
def duration_indices_delete(target_group, duration_seconds):
    """Delete duration index"""
    try:
        models.delete_duration_index(target_group, duration_seconds)
        return jsonify({"status": "ok"})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

# ---------- Seasonal Indices API ----------
@bp.route("/seasonal-indices", methods=["GET"])
def seasonal_indices_list():
    """Get all seasonal indices grouped by target group"""
    return jsonify(models.list_seasonal_indices())

@bp.route("/seasonal-indices/<target_group>/<int:month>", methods=["PATCH"])
def seasonal_indices_update(target_group, month):
    """Update seasonal index for specific target group and month"""
    data = request.get_json(force=True)
    index_value = data.get("index_value")
    description = data.get("description")
    
    if index_value is None:
        return jsonify({"status": "error", "message": "index_value required"}), 400
    
    try:
        models.update_seasonal_index(target_group, month, float(index_value), description)
        return jsonify({"status": "ok"})
    except ValueError as e:
        return jsonify({"status": "error", "message": str(e)}), 400

# ---------- Position Indices API ----------
@bp.route("/position-indices", methods=["GET"])
def position_indices_list():
    """Get all position indices grouped by target group"""
    return jsonify(models.list_position_indices())
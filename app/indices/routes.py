# app/indices/routes.py
from . import bp
from flask import render_template, request, jsonify
from app import models

# ---------- Page ----------
@bp.route("/indices", methods=["GET"])
def indices_page():
    return render_template("indices_admin.html")

# ---------- Channel Groups API ----------
@bp.route("/channel-groups", methods=["GET"])
def channel_groups_list():
    """Get all available channel groups for indices management"""
    return jsonify(models.list_channel_groups())

# ---------- Duration Indices API ----------
@bp.route("/duration-indices", methods=["GET"])
def duration_indices_list():
    """Get all duration indices grouped by channel group"""
    return jsonify(models.list_duration_indices())

@bp.route("/duration-indices", methods=["POST"])
def duration_indices_create():
    """Create or update duration index"""
    data = request.get_json(force=True)
    channel_group = data.get("channel_group")  # Changed from target_group to channel_group
    duration = data.get("duration_seconds")
    index_value = data.get("index_value")
    description = data.get("description", "")
    
    if not channel_group or duration is None or index_value is None:
        return jsonify({"status": "error", "message": "channel_group, duration_seconds and index_value required"}), 400
    
    try:
        models.update_duration_index(channel_group, int(duration), float(index_value), description.strip() or None)
        return jsonify({"status": "ok"}), 201
    except ValueError as e:
        return jsonify({"status": "error", "message": str(e)}), 400

@bp.route("/duration-indices/<channel_group>/<int:duration_seconds>", methods=["DELETE"])
def duration_indices_delete(channel_group, duration_seconds):
    """Delete duration index"""
    try:
        models.delete_duration_index(channel_group, duration_seconds)
        return jsonify({"status": "ok"})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

# ---------- Seasonal Indices API ----------
@bp.route("/seasonal-indices", methods=["GET"])
def seasonal_indices_list():
    """Get all seasonal indices grouped by channel group"""
    return jsonify(models.list_seasonal_indices())

@bp.route("/seasonal-indices/<channel_group>/<int:month>", methods=["PATCH"])
def seasonal_indices_update(channel_group, month):
    """Update seasonal index for specific channel group and month"""
    data = request.get_json(force=True)
    index_value = data.get("index_value")
    description = data.get("description")
    
    if index_value is None:
        return jsonify({"status": "error", "message": "index_value required"}), 400
    
    try:
        models.update_seasonal_index(channel_group, month, float(index_value), description)
        return jsonify({"status": "ok"})
    except ValueError as e:
        return jsonify({"status": "error", "message": str(e)}), 400

# ---------- Position Indices API ----------
@bp.route("/position-indices", methods=["GET"])
def position_indices_list():
    """Get all position indices grouped by channel group"""
    return jsonify(models.list_position_indices())
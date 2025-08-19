from . import bp
from flask import render_template, request, jsonify
from app import models
import sqlite3

# ---------------------------
# Page (HTML)
# ---------------------------
@bp.route("/channels", methods=["GET"])
def channels_page():
    return render_template("channel_groups.html")


# ---------------------------
# API: Channel Groups
# ---------------------------
@bp.route("/channel-groups", methods=["GET"])
def cg_list():
    return jsonify(models.list_channel_groups())

@bp.route("/channel-groups", methods=["POST"])
def cg_create():
    data = request.get_json(force=True)
    name = (data.get("name") or "").strip()
    if not name:
        return jsonify({"status": "error", "message": "name required"}), 400
    gid = models.upsert_channel_group(name)
    return jsonify({"status": "ok", "id": gid}), 201

@bp.route("/channel-groups/<int:gid>", methods=["PATCH"])
def cg_update(gid):
    data = request.get_json(force=True)
    try:
        models.update_channel_group(gid, (data.get("name") or "").strip())
        return jsonify({"status": "ok"})
    except sqlite3.IntegrityError:
        return jsonify({"status": "error", "message": "Group name must be unique"}), 409
    except ValueError as e:
        return jsonify({"status": "error", "message": str(e)}), 400

@bp.route("/channel-groups/<int:gid>", methods=["DELETE"])
def cg_delete(gid):
    try:
        models.delete_channel_group(gid)
        return jsonify({"status": "ok"})
    except ValueError as e:
        # Group used by TRP rates → block deletion
        return jsonify({"status": "error", "message": str(e)}), 409


# ---------------------------
# API: Channels in a Group
# ---------------------------
@bp.route("/channel-groups/<int:gid>/channels", methods=["GET"])
def ch_list(gid):
    return jsonify(models.list_channels(gid))

@bp.route("/channel-groups/<int:gid>/channels", methods=["POST"])
def ch_create(gid):
    data = request.get_json(force=True)
    name = (data.get("name") or "").strip()
    size = (data.get("size") or "").strip().lower()
    if not name or size not in ("big", "small"):
        return jsonify({"status": "error", "message": "name + size('big'|'small') required"}), 400
    try:
        models.create_channel(gid, name, size)
        return jsonify({"status": "ok"}), 201
    except sqlite3.IntegrityError:
        return jsonify({"status": "error", "message": "Channel already exists in this group"}), 409


# ---------------------------
# API: All Channels (for campaign wave forms)
# ---------------------------
@bp.route("/channels-api", methods=["GET"])
def all_channels():
    """Get all channels from all groups"""
    return jsonify(models.list_all_channels())

# ---------------------------
# API: Single Channel (update/delete)
# ---------------------------
@bp.route("/channels/<int:cid>", methods=["PATCH"])
def ch_update(cid):
    data = request.get_json(force=True)
    try:
        models.update_channel(
            cid,
            name=(data.get("name") if "name" in data else None),
            size=(data.get("size") if "size" in data else None),
        )
        return jsonify({"status": "ok"})
    except ValueError as e:
        return jsonify({"status": "error", "message": str(e)}), 400
    except sqlite3.IntegrityError:
        return jsonify({"status": "error", "message": "Duplicate channel name in this group"}), 409

@bp.route("/channels/<int:cid>", methods=["DELETE"])
def ch_delete(cid):
    models.delete_channel(cid)
    return jsonify({"status": "ok"})


# ---------------------------
# Dev seeder (used by UI button)
# ---------------------------
@bp.route("/dev/seed-channel-groups", methods=["POST"])
def dev_seed_cg():
    models.seed_channel_groups()
    return jsonify({"status": "ok"})

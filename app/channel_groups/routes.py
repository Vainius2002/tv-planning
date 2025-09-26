from . import bp
from flask import render_template, request, jsonify, Response
from app import models
import sqlite3
from io import BytesIO

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
# Excel Export for Channel Group
# ---------------------------
@bp.route("/test-excel", methods=["GET"])
def test_excel():
    """Simple test endpoint"""
    return jsonify({"status": "ok", "message": "Test endpoint works"}), 200

@bp.route("/channel-groups/<int:group_id>/export-excel", methods=["GET"])
def export_channel_group_excel(group_id):
    """Export Excel file for all campaigns using this channel group"""
    # Test immediate response - don't even import anything
    if group_id == 998:
        return jsonify({"status": "immediate_test", "message": "Route handler reached"}), 200

    import sys
    import traceback

    print(f"DEBUG ROUTE: Starting export for group_id={group_id}", file=sys.stderr, flush=True)

    # Quick test to see if the route is working at all
    if group_id == 999:
        print("DEBUG: Test response for group 999", file=sys.stderr, flush=True)
        return jsonify({"status": "test", "message": "Route is working"}), 200

    try:
        print(f"DEBUG ROUTE: About to call export function for group_id={group_id}", file=sys.stderr, flush=True)

        # Temporarily skip the actual Excel generation to test
        if group_id == 997:
            return jsonify({"status": "skip", "message": "Skipping Excel generation for test"}), 200

        excel_buffer = models.export_channel_group_excel(group_id)

        print(f"DEBUG ROUTE: Excel buffer created successfully", file=sys.stderr, flush=True)

        # Get group name for filename
        group = models.get_channel_group_by_id(group_id)
        group_name = group['name'] if group else f'Group_{group_id}'

        # Sanitize filename for HTTP headers (replace Lithuanian characters with ASCII equivalents)
        import re
        # Replace Lithuanian characters with ASCII equivalents
        char_replacements = {
            'ą': 'a', 'č': 'c', 'ę': 'e', 'ė': 'e', 'į': 'i', 'š': 's', 'ų': 'u', 'ū': 'u', 'ž': 'z',
            'Ą': 'A', 'Č': 'C', 'Ę': 'E', 'Ė': 'E', 'Į': 'I', 'Š': 'S', 'Ų': 'U', 'Ū': 'U', 'Ž': 'Z'
        }
        safe_group_name = group_name
        for lithuanian_char, ascii_char in char_replacements.items():
            safe_group_name = safe_group_name.replace(lithuanian_char, ascii_char)

        # Remove any remaining non-ASCII characters and replace spaces with underscores
        safe_group_name = re.sub(r'[^\w\-_\. ]', '', safe_group_name).replace(' ', '_')
        filename = f'{safe_group_name}_kanalu_ataskaita.xlsx'

        print(f"DEBUG ROUTE: Creating response with filename={filename}", file=sys.stderr, flush=True)

        response = Response(
            excel_buffer.getvalue(),
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            headers={
                'Content-Disposition': f'attachment; filename="{filename}"'
            }
        )

        print(f"DEBUG ROUTE: Response created, returning...", file=sys.stderr, flush=True)
        return response
    except Exception as e:
        print(f"ERROR in export_channel_group_excel: {str(e)}", file=sys.stderr, flush=True)
        traceback.print_exc(file=sys.stderr)
        return jsonify({"status": "error", "message": str(e)}), 500


# ---------------------------
# Dev seeder (used by UI button)
# ---------------------------
@bp.route("/dev/seed-channel-groups", methods=["POST"])
def dev_seed_cg():
    models.seed_channel_groups()
    return jsonify({"status": "ok"})

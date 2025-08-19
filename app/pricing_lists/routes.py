# app/pricing_lists/routes.py
from . import bp
from flask import render_template, request, jsonify
from app import models
import sqlite3

# Page (HTML)
@bp.route("/pricing", methods=["GET"])
def pricing_page():
    return render_template("pricing_lists.html")

# Lists
@bp.route("/pricing-lists", methods=["GET"])
def pl_list():
    return jsonify(models.list_pricing_lists())

@bp.route("/pricing-lists", methods=["POST"])
def pl_create():
    data = request.get_json(force=True)
    name = (data.get("name") or "").strip()
    if not name:
        return jsonify({"status":"error","message":"name required"}), 400
    try:
        new_id = models.create_pricing_list(name)
        return jsonify({"status":"ok","id":new_id}), 201
    except sqlite3.IntegrityError:
        return jsonify({"status":"error","message":"name must be unique"}), 409

@bp.route("/pricing-lists/<int:list_id>", methods=["DELETE"])
def pl_delete(list_id):
    models.delete_pricing_list(list_id)
    return jsonify({"status":"ok"})

@bp.route("/pricing-lists/<int:list_id>/duplicate", methods=["POST"])
def pl_duplicate(list_id):
    data = request.get_json(force=True)
    new_name = (data.get("name") or "").strip()
    if not new_name:
        return jsonify({"status":"error","message":"new name required"}), 400
    try:
        new_id = models.duplicate_pricing_list(list_id, new_name)
        return jsonify({"status":"ok","id":new_id})
    except sqlite3.IntegrityError:
        return jsonify({"status":"error","message":"name must be unique"}), 409

@bp.route("/pricing-lists/<int:list_id>/reimport", methods=["POST"])
def pl_reimport(list_id):
    """Re-import all TRP rates to existing pricing list"""
    try:
        models.import_trp_rates_to_pricing_list(list_id)
        return jsonify({"status":"ok"})
    except Exception as e:
        return jsonify({"status":"error","message":str(e)}), 500

# Items
@bp.route("/pricing-lists/<int:list_id>/items", methods=["GET"])
def pli_list(list_id):
    items = models.list_pricing_list_items(list_id)
    # Convert owner string back to channel_group_id for frontend compatibility
    for item in items:
        if 'owner' in item:
            try:
                item['channel_group_id'] = int(item['owner'])
            except (ValueError, TypeError):
                item['channel_group_id'] = None
    return jsonify(items)

@bp.route("/pricing-lists/<int:list_id>/items", methods=["POST"])
def pli_create(list_id):
    data = request.get_json(force=True)
    try:
        # Get channel_group_id from request and convert to owner string
        channel_group_id = data.get("channel_group_id")
        if not channel_group_id:
            raise ValueError("channel_group_id is required")
        
        item_id = models.create_pricing_list_item(  # Use create instead of upsert for new items
            pricing_list_id=list_id,
            owner=str(channel_group_id),  # Convert channel_group_id to owner string
            target_group=data.get("target_group", "").strip(),
            primary_label=data.get("primary_label", "").strip(),
            secondary_label=data.get("secondary_label", "").strip() or None,
            share_primary=data.get("share_primary"),
            share_secondary=data.get("share_secondary"),
            prime_share_primary=data.get("prime_share_primary"),
            prime_share_secondary=data.get("prime_share_secondary"),
            price_per_sec_eur=data.get("price_per_sec_eur"),
        )
        return jsonify({"status":"ok", "id": item_id}), 201
    except ValueError as e:
        return jsonify({"status":"error","message":str(e)}), 400
    except sqlite3.IntegrityError:
        return jsonify({"status":"error","message":"Duplicate (list, group, target) - an item with this combination already exists"}), 409

@bp.route("/pricing-list-items/<int:item_id>", methods=["PATCH"])
def pli_update(item_id):
    data = request.get_json(force=True)
    try:
        models.update_pricing_list_item(item_id, data)
        return jsonify({"status":"ok"})
    except ValueError as e:
        return jsonify({"status":"error","message":str(e)}), 400

@bp.route("/pricing-list-items/<int:item_id>", methods=["DELETE"])
def pli_delete(item_id):
    models.delete_pricing_list_item(item_id)
    return jsonify({"status":"ok"})

# Optional one-time migration from legacy trp_rates
@bp.route("/dev/migrate-trp-to-pricing-list", methods=["POST"])
def dev_migrate():
    data = request.get_json(silent=True) or {}
    name = (data.get("name") or "Imported from TRP Admin").strip()
    new_id = models.migrate_trp_rates_to_pricing_list(name)
    return jsonify({"status":"ok","list_id":new_id,"name":name})

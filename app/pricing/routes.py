# app/pricing_lists/routes.py
from . import bp
from flask import render_template, request, jsonify
from app import models
import sqlite3

# Page
@bp.route("/pricing-lists-admin", methods=["GET"])
def pricing_lists_admin_page():
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

# Items
@bp.route("/pricing-lists/<int:list_id>/items", methods=["GET"])
def pli_list(list_id):
    return jsonify(models.list_pricing_list_items(list_id))

@bp.route("/pricing-lists/<int:list_id>/items", methods=["POST"])
def pli_create(list_id):
    data = request.get_json(force=True)
    try:
        models.create_pricing_list_item(
            list_id=list_id,
            channel_group_id=int(data.get("channel_group_id")),
            target_group=(data.get("target_group") or "").strip(),
            primary_label=(data.get("primary_label") or "").strip(),
            secondary_label=(data.get("secondary_label") or "").strip() or None,
            share_primary=data.get("share_primary"),
            share_secondary=data.get("share_secondary"),
            prime_share_primary=data.get("prime_share_primary"),
            prime_share_secondary=data.get("prime_share_secondary"),
            price_per_sec_eur=data.get("price_per_sec_eur"),
        )
        return jsonify({"status":"ok"}), 201
    except ValueError as e:
        return jsonify({"status":"error","message":str(e)}), 400
    except sqlite3.IntegrityError:
        return jsonify({"status":"error","message":"Duplicate (list, group, target)"}), 409

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

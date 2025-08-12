# app/campaigns/routes.py
from . import bp
from flask import render_template, request, jsonify
from app import models

# ---------- Page ----------
@bp.route("/campaigns-admin", methods=["GET"])
def campaigns_admin_page():
    return render_template("campaigns_admin.html")

# ---------- Pricing list helpers (read-only) ----------
@bp.route("/pricing-lists", methods=["GET"])
def pl_list():
    return jsonify(models.list_pricing_lists())

@bp.route("/pricing-lists/<int:pl_id>/owners", methods=["GET"])
def pl_owners(pl_id):
    return jsonify(models.list_pricing_owners(pl_id))

@bp.route("/pricing-lists/<int:pl_id>/targets", methods=["GET"])
def pl_targets(pl_id):
    owner = request.args.get("owner","")
    return jsonify(models.list_pricing_targets(pl_id, owner))

# ---------- Campaigns ----------
@bp.route("/campaigns", methods=["GET"])
def campaigns_list():
    return jsonify(models.list_campaigns())

@bp.route("/campaigns", methods=["POST"])
def campaigns_create():
    data = request.get_json(force=True)
    name = (data.get("name") or "").strip()
    pl_id = data.get("pricing_list_id")
    if not name or not pl_id:
        return jsonify({"status":"error","message":"name and pricing_list_id required"}), 400
    cid = models.create_campaign(name, pl_id, data.get("start_date"), data.get("end_date"))
    return jsonify({"status":"ok","id":cid}), 201

@bp.route("/campaigns/<int:cid>", methods=["PATCH"])
def campaigns_update(cid):
    data = request.get_json(force=True)
    models.update_campaign(cid, data)
    return jsonify({"status":"ok"})

@bp.route("/campaigns/<int:cid>", methods=["DELETE"])
def campaigns_delete(cid):
    models.delete_campaign(cid)
    return jsonify({"status":"ok"})

# ---------- Waves ----------
@bp.route("/campaigns/<int:cid>/waves", methods=["GET"])
def waves_list(cid):
    return jsonify(models.list_waves(cid))

@bp.route("/campaigns/<int:cid>/waves", methods=["POST"])
def waves_create(cid):
    data = request.get_json(force=True)
    wid = models.create_wave(cid, data.get("name"), data.get("start_date"), data.get("end_date"))
    return jsonify({"status":"ok","id":wid}), 201

@bp.route("/waves/<int:wid>", methods=["PATCH"])
def waves_update(wid):
    data = request.get_json(force=True)
    models.update_wave(wid, data)
    return jsonify({"status":"ok"})

@bp.route("/waves/<int:wid>", methods=["DELETE"])
def waves_delete(wid):
    models.delete_wave(wid)
    return jsonify({"status":"ok"})

# ---------- Wave items ----------
@bp.route("/waves/<int:wid>/items", methods=["GET"])
def wave_items_list(wid):
    return jsonify(models.list_wave_items(wid))

@bp.route("/waves/<int:wid>/items", methods=["POST"])
def wave_items_create(wid):
    data = request.get_json(force=True)
    owner = (data.get("owner") or "").strip()
    tg    = (data.get("target_group") or "").strip()
    trps  = data.get("trps")
    if not owner or not tg or trps in (None, ""):
        return jsonify({"status":"error","message":"owner, target_group, trps required"}), 400
    try:
        iid = models.create_wave_item_prefill(wid, owner, tg, trps)
        return jsonify({"status":"ok","id":iid}), 201
    except ValueError as e:
        return jsonify({"status":"error","message":str(e)}), 400

@bp.route("/wave-items/<int:iid>", methods=["PATCH"])
def wave_items_update(iid):
    data = request.get_json(force=True)
    models.update_wave_item(iid, data)
    return jsonify({"status":"ok"})

@bp.route("/wave-items/<int:iid>", methods=["DELETE"])
def wave_items_delete(iid):
    models.delete_wave_item(iid)
    return jsonify({"status":"ok"})

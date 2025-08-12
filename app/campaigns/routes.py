# app/campaigns/routes.py
from . import bp
from flask import render_template, request, jsonify, send_file
from app import models
from datetime import datetime

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

# Discounts
@bp.route("/campaigns/<int:cid>/discounts", methods=["GET"])
def get_campaign_discounts(cid):
    """Get all discounts for a campaign"""
    return jsonify(models.get_discounts_for_campaign(cid))

@bp.route("/campaigns/<int:cid>/discounts", methods=["POST"])
def create_campaign_discount(cid):
    """Create a campaign-level discount"""
    data = request.get_json(force=True)
    discount_type = data.get("discount_type", "client")
    discount_percentage = float(data.get("discount_percentage", 0))
    
    try:
        discount_id = models.create_discount(
            campaign_id=cid,
            discount_type=discount_type,
            discount_percentage=discount_percentage
        )
        return jsonify({"status":"ok", "id": discount_id}), 201
    except ValueError as e:
        return jsonify({"status":"error", "message": str(e)}), 400

@bp.route("/waves/<int:wid>/discounts", methods=["GET"])
def get_wave_discounts(wid):
    """Get all discounts for a wave"""
    return jsonify(models.get_discounts_for_wave(wid))

@bp.route("/waves/<int:wid>/discounts", methods=["POST"])
def create_wave_discount(wid):
    """Create a wave-level discount"""
    data = request.get_json(force=True)
    discount_type = data.get("discount_type", "client")
    discount_percentage = float(data.get("discount_percentage", 0))
    
    # Get campaign_id for this wave
    with models.get_db() as db:
        wave = db.execute("SELECT campaign_id FROM waves WHERE id = ?", (wid,)).fetchone()
        if not wave:
            return jsonify({"status":"error", "message":"Wave not found"}), 404
    
    try:
        discount_id = models.create_discount(
            campaign_id=wave['campaign_id'],
            wave_id=wid,
            discount_type=discount_type,
            discount_percentage=discount_percentage
        )
        return jsonify({"status":"ok", "id": discount_id}), 201
    except ValueError as e:
        return jsonify({"status":"error", "message": str(e)}), 400

@bp.route("/discounts/<int:did>", methods=["PATCH"])
def update_discount(did):
    """Update a discount"""
    data = request.get_json(force=True)
    discount_percentage = float(data.get("discount_percentage", 0))
    
    models.update_discount(did, discount_percentage)
    return jsonify({"status":"ok"})

@bp.route("/discounts/<int:did>", methods=["DELETE"])
def delete_discount(did):
    """Delete a discount"""
    models.delete_discount(did)
    return jsonify({"status":"ok"})

@bp.route("/waves/<int:wid>/total", methods=["GET"])
def get_wave_total(wid):
    """Get wave total with discounts applied"""
    return jsonify(models.calculate_wave_total_with_discounts(wid))

# Campaign Status
@bp.route("/campaigns/<int:cid>/status", methods=["PATCH"])
def update_campaign_status(cid):
    """Update campaign status"""
    data = request.get_json(force=True)
    status = data.get("status", "draft")
    
    try:
        models.update_campaign_status(cid, status)
        return jsonify({"status": "ok"})
    except ValueError as e:
        return jsonify({"status": "error", "message": str(e)}), 400

# Reports
@bp.route("/campaigns/<int:cid>/export/client-excel", methods=["GET"])
def export_client_excel(cid):
    """Export client Excel report"""
    try:
        excel_file = models.generate_client_excel_report(cid)
        if not excel_file:
            return jsonify({"status": "error", "message": "Campaign not found"}), 404
        
        # Get campaign name for filename
        campaign_data = models.get_campaign_report_data(cid)
        campaign_name = campaign_data['campaign']['name'] if campaign_data else f"Campaign_{cid}"
        
        # Clean filename
        safe_name = "".join(c for c in campaign_name if c.isalnum() or c in (' ', '-', '_')).rstrip()
        filename = f"TV_Plan_{safe_name}_{datetime.now().strftime('%Y%m%d')}.xlsx"
        
        return send_file(
            excel_file,
            as_attachment=True,
            download_name=filename,
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@bp.route("/campaigns/<int:cid>/export/agency-csv", methods=["GET"])
def export_agency_csv(cid):
    """Export agency CSV order file"""
    try:
        csv_file = models.generate_agency_csv_order(cid)
        if not csv_file:
            return jsonify({"status": "error", "message": "Campaign not found"}), 404
        
        # Get campaign name for filename
        campaign_data = models.get_campaign_report_data(cid)
        campaign_name = campaign_data['campaign']['name'] if campaign_data else f"Campaign_{cid}"
        
        # Clean filename
        safe_name = "".join(c for c in campaign_name if c.isalnum() or c in (' ', '-', '_')).rstrip()
        filename = f"TV_Order_{safe_name}_{datetime.now().strftime('%Y%m%d')}.csv"
        
        return send_file(
            csv_file,
            as_attachment=True,
            download_name=filename,
            mimetype='text/csv; charset=utf-8'
        )
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

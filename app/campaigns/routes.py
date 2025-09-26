# app/campaigns/routes.py
from . import bp
from flask import render_template, request, jsonify, send_file
from app import models
from app.projects_crm_service import (
    get_tv_planner_campaigns, 
    get_local_campaign_id, 
    sync_wave_to_projects_crm_plan,
    sync_wave_deletion_to_projects_crm,
    get_projects_crm_campaign_id_from_local
)
from datetime import datetime

# ---------- Page ----------
@bp.route("/campaigns", methods=["GET"])
def campaigns_page():
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

# ---------- Campaigns API ----------
@bp.route("/campaigns-api", methods=["GET"])
def campaigns_list():
    # Get local TV-Planner campaigns
    local_campaigns = models.list_campaigns()
    print(f"Found {len(local_campaigns)} local campaigns")
    
    # Get campaigns from Projects-CRM
    try:
        projects_crm_campaigns = get_tv_planner_campaigns()
        print(f"Found {len(projects_crm_campaigns)} Projects-CRM campaigns")
    except Exception as e:
        print(f"Error fetching Projects-CRM campaigns: {e}")
        projects_crm_campaigns = []
    
    # Deduplicate campaigns by detecting potential matches
    # Projects-CRM campaigns have names like "Campaign Name (CODE)" 
    # Local campaigns that were synced might have the same name
    deduplicated_campaigns = []
    local_campaign_names = {c['name'] for c in local_campaigns}
    
    # Add all local campaigns first
    deduplicated_campaigns.extend(local_campaigns)
    
    # Add Projects-CRM campaigns only if they don't match existing local campaigns
    for crm_campaign in projects_crm_campaigns:
        crm_name = crm_campaign['name']
        
        # Check if this CRM campaign matches any local campaign
        is_duplicate = False
        
        # Direct name match
        if crm_name in local_campaign_names:
            is_duplicate = True
        
        # Check for potential sync matches - local campaign might be named the same
        # as the CRM campaign without the (CODE) suffix
        base_crm_name = crm_name
        if ' (' in crm_name and crm_name.endswith(')'):
            base_crm_name = crm_name.split(' (')[0]
            if base_crm_name in local_campaign_names:
                is_duplicate = True
        
        # Also check the reverse - if any local campaign contains the CRM name
        for local_name in local_campaign_names:
            if base_crm_name.lower() in local_name.lower() or local_name.lower() in base_crm_name.lower():
                # Additional check: both should have similar dates to be considered duplicates
                for local_campaign in local_campaigns:
                    if (local_campaign['name'] == local_name and 
                        local_campaign.get('start_date') == crm_campaign.get('start_date')):
                        is_duplicate = True
                        break
        
        if not is_duplicate:
            deduplicated_campaigns.append(crm_campaign)
        else:
            print(f"Skipping duplicate campaign: {crm_name}")
    
    crm_added = len(deduplicated_campaigns) - len(local_campaigns)
    crm_skipped = len(projects_crm_campaigns) - crm_added
    print(f"Final result: {len(deduplicated_campaigns)} total campaigns ({len(local_campaigns)} local + {crm_added} CRM, {crm_skipped} CRM duplicates skipped)")
    return jsonify(deduplicated_campaigns)


@bp.route("/campaigns-api/<int:cid>", methods=["PATCH"])
def campaigns_update(cid):
    data = request.get_json(force=True)
    models.update_campaign(cid, data)
    return jsonify({"status":"ok"})

@bp.route("/campaigns-api/<int:cid>", methods=["DELETE"])
def campaigns_delete(cid):
    models.delete_campaign(cid)
    return jsonify({"status":"ok"})

# ---------- Waves ----------
@bp.route("/campaigns/<cid>/waves", methods=["GET"])
def waves_list(cid):
    try:
        local_cid = get_local_campaign_id(cid)
        return jsonify(models.list_waves(local_cid))
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@bp.route("/campaigns/<cid>/waves", methods=["POST"])
def waves_create(cid):
    try:
        local_cid = get_local_campaign_id(cid)
        data = request.get_json(force=True)
        
        wave_name = data.get("name")
        wave_start_date = data.get("start_date")
        wave_end_date = data.get("end_date")
        
        print(f"Creating wave: {wave_name} for campaign {cid} (local: {local_cid})")
        
        # Create wave in TV-Planner
        wid = models.create_wave(local_cid, wave_name, wave_start_date, wave_end_date)
        print(f"Created wave with ID: {wid}")
        
        # Sync to Projects-CRM if this is a Projects-CRM campaign
        original_cid = cid if str(cid).startswith('crm_') else get_projects_crm_campaign_id_from_local(local_cid)
        
        if original_cid:
            try:
                plan_data = sync_wave_to_projects_crm_plan(
                    campaign_id=original_cid,
                    wave_name=wave_name,
                    wave_start_date=wave_start_date,
                    wave_end_date=wave_end_date
                )
                if plan_data:
                    print(f"Successfully synced wave '{wave_name}' to Projects-CRM as plan '{plan_data['name']}'")
                else:
                    print(f"Failed to sync wave '{wave_name}' to Projects-CRM")
            except Exception as sync_error:
                print(f"Error syncing wave to Projects-CRM: {sync_error}")
                # Don't fail the wave creation if sync fails
        
        return jsonify({"status":"ok","id":wid}), 201
        
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@bp.route("/waves/<int:wid>", methods=["PATCH"])
def waves_update(wid):
    data = request.get_json(force=True)
    models.update_wave(wid, data)
    return jsonify({"status":"ok"})

@bp.route("/waves/<int:wid>", methods=["DELETE"])
def waves_delete(wid):
    try:
        print(f"Deleting wave {wid}")
        
        # Get wave information before deleting it
        from app import models
        wave = models.list_waves_for_deletion_sync(wid)
        print(f"Wave info: {wave}")
        
        if wave:
            wave_name = wave.get('name')
            campaign_id = wave.get('campaign_id')
            print(f"Wave name: {wave_name}, Campaign ID: {campaign_id}")
            
            # Delete the wave from TV-Planner
            models.delete_wave(wid)
            print("Wave deleted from database")
            
            # Sync deletion to Projects-CRM if this is a Projects-CRM campaign
            if campaign_id and wave_name:
                original_cid = get_projects_crm_campaign_id_from_local(campaign_id)
                if original_cid:
                    try:
                        result = sync_wave_deletion_to_projects_crm(original_cid, wave_name)
                        if result:
                            print(f"Successfully deleted plan '{wave_name}' from Projects-CRM")
                        else:
                            print(f"Plan '{wave_name}' not found in Projects-CRM (may have been already deleted)")
                    except Exception as sync_error:
                        print(f"Error syncing wave deletion to Projects-CRM: {sync_error}")
                        # Don't fail the wave deletion if sync fails
        else:
            # Wave not found, just try to delete it anyway
            models.delete_wave(wid)
            
        return jsonify({"status":"ok"})
        
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

# ---------- Wave items ----------
@bp.route("/waves/<int:wid>/items", methods=["GET"])
def wave_items_list(wid):
    return jsonify(models.list_wave_items(wid))

@bp.route("/waves/<int:wid>/items", methods=["POST"])
def wave_items_create(wid):
    data = request.get_json(force=True)
    
    # Get required fields
    channel_group = data.get("channel_group")
    target_group = (data.get("target_group") or "").strip()
    trps = data.get("trps")
    
    if not channel_group or not target_group or trps in (None, ""):
        return jsonify({"status":"error","message":"channel_group, target_group, trps required"}), 400
    
    # Get all Excel fields with defaults
    excel_data = {
        "channel_group": channel_group,
        "target_group": target_group,
        "trps": float(trps),
        "channel_share": float(data.get("channel_share", 0.75)),
        "pt_zone_share": float(data.get("pt_zone_share", 0.55)),
        "clip_duration": int(data.get("clip_duration", 10)),
        "tvc_id": data.get("tvc_id"),  # TVC ID from database
        "affinity1": data.get("affinity1"),
        "affinity2": data.get("affinity2"),
        "affinity3": data.get("affinity3"),
        "duration_index": float(data.get("duration_index", 1.25)),
        "seasonal_index": float(data.get("seasonal_index", 0.9)),
        "trp_purchase_index": float(data.get("trp_purchase_index", 0.95)),
        "advance_purchase_index": float(data.get("advance_purchase_index", 0.95)),
        "position_index": float(data.get("position_index", 1.0)),
        "client_discount": float(data.get("client_discount", 0)),
        "agency_discount": float(data.get("agency_discount", 0)),
        # TG demographic data from Excel/form
        "tg_size_thousands": float(data.get("tg_size_thousands", 0)),
        "tg_share_percent": float(data.get("tg_share_percent", 0)),
        "tg_sample_size": int(data.get("tg_sample_size", 0))
    }
    
    try:
        iid = models.create_wave_item_excel(wid, excel_data)
        return jsonify({"status":"ok","id":iid}), 201
    except ValueError as e:
        return jsonify({"status":"error","message":str(e)}), 400

@bp.route("/wave-items/<int:iid>", methods=["PATCH"])
def wave_items_update(iid):
    try:
        data = request.get_json(force=True)
        print(f"DEBUG: wave_items_update route called with iid={iid}, data={data}")
        models.update_wave_item(iid, data)
        print(f"DEBUG: update_wave_item completed successfully")
        return jsonify({"status":"ok"})
    except Exception as e:
        print(f"ERROR in wave_items_update: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({"status":"error", "message": str(e)}), 500

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

@bp.route("/waves/<int:wid>/recalculate-discounts", methods=["POST"])
def recalculate_wave_discounts(wid):
    """Recalculate wave item prices with wave-level discounts"""
    try:
        models.recalculate_wave_item_prices_with_discounts(wid)
        return jsonify({"status": "ok"})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

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
@bp.route("/campaigns/<cid>/export/client-excel", methods=["GET"])
def export_client_excel(cid):
    """Export client Excel report"""
    import sys
    print(f"DEBUG: Client Excel export requested for cid={cid}", file=sys.stderr, flush=True)

    try:
        local_cid = get_local_campaign_id(cid)
        print(f"DEBUG: Local cid={local_cid}", file=sys.stderr, flush=True)

        excel_file = models.generate_client_excel_report(local_cid)
        print(f"DEBUG: Excel file generated: {excel_file}", file=sys.stderr, flush=True)
        if not excel_file:
            return jsonify({"status": "error", "message": "Campaign not found"}), 404
        
        # Get campaign name for filename
        campaign_data = models.get_campaign_report_data(local_cid)
        campaign_name = campaign_data['campaign']['name'] if campaign_data else f"Campaign_{local_cid}"

        # Replace Lithuanian characters with ASCII equivalents
        char_replacements = {
            'ą': 'a', 'č': 'c', 'ę': 'e', 'ė': 'e', 'į': 'i', 'š': 's', 'ų': 'u', 'ū': 'u', 'ž': 'z',
            'Ą': 'A', 'Č': 'C', 'Ę': 'E', 'Ė': 'E', 'Į': 'I', 'Š': 'S', 'Ų': 'U', 'Ū': 'U', 'Ž': 'Z'
        }
        safe_name = campaign_name
        for lithuanian_char, ascii_char in char_replacements.items():
            safe_name = safe_name.replace(lithuanian_char, ascii_char)

        # Clean filename - keep only alphanumeric, spaces, hyphens, underscores
        safe_name = "".join(c for c in safe_name if c.isalnum() or c in (' ', '-', '_')).rstrip()
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

# TVCs
@bp.route("/campaigns/<cid>/tvcs", methods=["GET"])
def list_tvcs(cid):
    """List all TVCs for a campaign"""
    try:
        local_cid = get_local_campaign_id(cid)
        return jsonify(models.list_campaign_tvcs(local_cid))
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@bp.route("/campaigns/<cid>/tvcs", methods=["POST"])
def create_tvc(cid):
    """Create a new TVC for a campaign"""
    data = request.get_json(force=True)
    name = data.get("name", "").strip()
    duration = data.get("duration", 0)
    
    try:
        local_cid = get_local_campaign_id(cid)
        tvc_id = models.create_tvc(local_cid, name, int(duration))
        return jsonify({"status": "ok", "id": tvc_id}), 201
    except ValueError as e:
        return jsonify({"status": "error", "message": str(e)}), 400
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@bp.route("/tvcs/<int:tvc_id>", methods=["PATCH"])
def update_tvc(tvc_id):
    """Update a TVC"""
    data = request.get_json(force=True)
    name = data.get("name")
    duration = data.get("duration")
    
    try:
        if duration is not None:
            duration = int(duration)
        models.update_tvc(tvc_id, name, duration)
        return jsonify({"status": "ok"})
    except ValueError as e:
        return jsonify({"status": "error", "message": str(e)}), 400

@bp.route("/tvcs/<int:tvc_id>", methods=["DELETE"])
def delete_tvc(tvc_id):
    """Delete a TVC"""
    models.delete_tvc(tvc_id)
    return jsonify({"status": "ok"})

# Indices for auto-population
@bp.route("/waves/<int:wid>/indices", methods=["GET"])
def get_wave_indices(wid):
    """Get duration and seasonal indices for wave item creation"""
    target_group = request.args.get("target_group")
    duration_seconds = request.args.get("duration_seconds", type=int)
    
    if not target_group or duration_seconds is None:
        return jsonify({"status": "error", "message": "target_group and duration_seconds required"}), 400
    
    # Get wave start and end dates for seasonal index calculation
    with models.get_db() as db:
        wave = db.execute("SELECT start_date, end_date FROM waves WHERE id = ?", (wid,)).fetchone()
        start_date = wave["start_date"] if wave else None
        end_date = wave["end_date"] if wave else None
        
        # Find the channel group for this target group from TRP rates
        # We need this because indices are now stored by channel group, not target group
        channel_group_row = db.execute("""
            SELECT DISTINCT owner FROM trp_rates WHERE target_group = ? LIMIT 1
        """, (target_group,)).fetchone()
        
        if not channel_group_row:
            return jsonify({"status": "error", "message": f"No channel group found for target group: {target_group}"}), 400
            
        channel_group = channel_group_row["owner"]
    
    try:
        indices = models.get_indices_for_wave_item(channel_group, duration_seconds, start_date, end_date)
        return jsonify({
            "status": "ok",
            "duration_index": indices["duration_index"],
            "seasonal_index": indices["seasonal_index"]
        })
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

# TRP Calendar Distribution
@bp.route("/campaigns/<int:cid>/trp-distribution", methods=["POST"])
def save_trp_distribution_api(cid):
    """Save TRP distribution for a campaign"""
    data = request.get_json(force=True)
    trp_data = data.get("trp_data", {})
    
    try:
        models.save_trp_distribution(cid, trp_data)
        return jsonify({"status": "ok"})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@bp.route("/campaigns/<int:cid>/trp-distribution", methods=["GET"])
def load_trp_distribution_api(cid):
    """Load TRP distribution for a campaign"""
    try:
        trp_data = models.load_trp_distribution(cid)
        return jsonify({"status": "ok", "data": trp_data})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

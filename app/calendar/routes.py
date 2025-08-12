# app/calendar/routes.py
from . import bp
from flask import render_template, request, jsonify
from app import models
from datetime import datetime, timedelta
import calendar

@bp.route("/calendar", methods=["GET"])
def calendar_page():
    """Calendar view page"""
    return render_template("calendar.html")

@bp.route("/calendar/events", methods=["GET"])
def calendar_events():
    """Get calendar events (campaigns and waves) for a specific month/year"""
    year = int(request.args.get('year', datetime.now().year))
    month = int(request.args.get('month', datetime.now().month))
    
    # Get all campaigns with their waves
    campaigns = models.list_campaigns()
    events = []
    
    for campaign in campaigns:
        # Add campaign as event if it has dates
        if campaign.get('start_date') or campaign.get('end_date'):
            events.append({
                'id': f"campaign_{campaign['id']}",
                'title': f"📺 {campaign['name']}",
                'type': 'campaign',
                'campaign_id': campaign['id'],
                'start': campaign.get('start_date'),
                'end': campaign.get('end_date'),
                'status': campaign.get('status', 'draft'),
                'url': f"/trp-admin/campaigns-admin?campaign={campaign['id']}"
            })
            
        # Get waves for this campaign
        waves = models.list_waves(campaign['id'])
        for wave in waves:
            if wave.get('start_date') or wave.get('end_date'):
                events.append({
                    'id': f"wave_{wave['id']}",
                    'title': f"🌊 {wave['name'] or 'Banga'}",
                    'type': 'wave',
                    'campaign_id': campaign['id'],
                    'campaign_name': campaign['name'],
                    'wave_id': wave['id'],
                    'start': wave.get('start_date'),
                    'end': wave.get('end_date'),
                    'url': f"/trp-admin/campaigns-admin?campaign={campaign['id']}&wave={wave['id']}"
                })
    
    return jsonify(events)

@bp.route("/calendar/month/<int:year>/<int:month>", methods=["GET"])
def calendar_month_data(year, month):
    """Get calendar structure for a specific month"""
    # Create calendar matrix
    cal = calendar.monthcalendar(year, month)
    month_name = calendar.month_name[month]
    
    return jsonify({
        'year': year,
        'month': month,
        'month_name': month_name,
        'calendar': cal,
        'prev_month': month - 1 if month > 1 else 12,
        'prev_year': year if month > 1 else year - 1,
        'next_month': month + 1 if month < 12 else 1,
        'next_year': year if month < 12 else year + 1
    })
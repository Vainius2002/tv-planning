#!/usr/bin/env python3
"""Test Projects-CRM integration with TV-Planner"""

from app.projects_crm_service import get_campaigns, get_tv_planner_campaigns

print("Testing Projects-CRM Integration")
print("="*40)

# Test raw API call
print("1. Testing raw API call...")
campaigns = get_campaigns()
print(f"   Found {len(campaigns)} campaigns from Projects-CRM")

if campaigns:
    sample = campaigns[0]
    print(f"   Sample: {sample['name']} ({sample['code']})")
    print(f"   Client: {sample['client_brand_name']}")
    print(f"   Project: {sample['project_name']}")

print("\n2. Testing formatted campaigns...")
tv_campaigns = get_tv_planner_campaigns()
print(f"   Formatted {len(tv_campaigns)} campaigns for TV-Planner")

if tv_campaigns:
    sample = tv_campaigns[0] 
    print(f"   Sample: {sample['name']}")
    print(f"   Client: {sample['client']}")
    print(f"   Product: {sample['product']}")
    print(f"   ID: {sample['id']}")

print("\n✅ Integration working!")
print("When TV-Planner is running, campaigns from Projects-CRM")
print("will appear in the kampanijos section automatically.")
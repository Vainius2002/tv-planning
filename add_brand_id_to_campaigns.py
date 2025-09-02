#!/usr/bin/env python3
"""
Add brand_id field to campaigns table for proper tracking of Agency CRM brands
"""

import sqlite3
import os

def add_brand_id_to_campaigns():
    """Add brand_id field to campaigns table"""
    
    try:
        print("🔧 Adding brand_id field to campaigns table...")
        
        db_path = '/home/vainiusl/py_projects/tv-planner/app/tv-calc.db'
        if not os.path.exists(db_path):
            print(f"❌ Database not found: {db_path}")
            return False
        
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Check if brand_id column already exists
        cursor.execute("PRAGMA table_info(campaigns)")
        columns = [column[1] for column in cursor.fetchall()]
        
        if 'brand_id' in columns:
            print("✅ brand_id column already exists")
            return True
        
        # Add brand_id column
        cursor.execute("ALTER TABLE campaigns ADD COLUMN brand_id INTEGER")
        print("✅ Added brand_id column")
        
        # Try to populate existing brand_ids based on product names
        # This is a best-effort match using the brand names
        print("🔄 Attempting to populate brand_ids for existing campaigns...")
        
        # Connect to Agency CRM to get brand mappings
        agency_db_path = '/home/vainiusl/py_projects/agency-crm/instance/agency_crm.db'
        if os.path.exists(agency_db_path):
            agency_conn = sqlite3.connect(agency_db_path)
            agency_cursor = agency_conn.cursor()
            
            # Get brand name to ID mapping
            agency_cursor.execute("SELECT id, name FROM brands")
            brand_map = {row[1]: row[0] for row in agency_cursor.fetchall()}
            
            # Update campaigns where we can match the product name to a brand
            updated = 0
            cursor.execute("SELECT id, product FROM campaigns WHERE product IS NOT NULL")
            for campaign_id, product in cursor.fetchall():
                if product in brand_map:
                    brand_id = brand_map[product]
                    cursor.execute("UPDATE campaigns SET brand_id = ? WHERE id = ?", 
                                 (brand_id, campaign_id))
                    updated += 1
            
            agency_conn.close()
            print(f"✅ Updated {updated} existing campaigns with brand_ids")
        
        conn.commit()
        conn.close()
        
        print("✅ Migration completed successfully!")
        return True
        
    except Exception as e:
        print(f"❌ Error during migration: {e}")
        return False

if __name__ == "__main__":
    import sys
    
    success = add_brand_id_to_campaigns()
    
    if not success:
        sys.exit(1)
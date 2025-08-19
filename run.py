from app import create_app
from app.models import init_db, migrate_add_tvc_id_to_wave_items, migrate_add_campaign_fields, migrate_add_wave_item_fields, migrate_add_pricing_indices, migrate_add_indices_tables

app = create_app()

if __name__ == "__main__":
    # Run migrations
    init_db()
    migrate_add_tvc_id_to_wave_items()
    migrate_add_campaign_fields()
    migrate_add_wave_item_fields()
    migrate_add_pricing_indices()
    migrate_add_indices_tables()
    
    app.run(debug=True, host="0.0.0.0", port=5004)
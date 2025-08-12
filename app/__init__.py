from flask import Flask
from . import models

def create_app():
    app = Flask(__name__)
    
    models.init_db()
    models.migrate_add_tvc_id_to_wave_items()  # Add tvc_id column to wave_items

    # Import blueprints from each package
    from app.about import bp as about_bp
    from app.trp_groups import bp as trp_admin
    from app.channel_groups import bp as channel_groups_bp
    from app.pricing_lists import bp as pricing_lists_bp
    from app.campaigns import bp as campaigns_bp
    from app.calendar import bp as calendar_bp

    # Register blueprints
    app.register_blueprint(about_bp, url_prefix="/about")
    app.register_blueprint(trp_admin, url_prefix="/trp-admin")
    app.register_blueprint(channel_groups_bp, url_prefix="/trp-admin")
    app.register_blueprint(pricing_lists_bp, url_prefix="/trp-admin")
    app.register_blueprint(campaigns_bp, url_prefix="/trp-admin")
    app.register_blueprint(calendar_bp, url_prefix="/trp-admin")
    
    

    @app.route("/")
    def home():
        return "Main page"

    return app

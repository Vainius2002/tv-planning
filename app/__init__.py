from flask import Flask
from . import models

def create_app():
    app = Flask(__name__)
    
    models.init_db()

    # Import blueprints from each package
    from app.about import bp as about_bp
    from app.trp_groups import bp as trp_admin

    # Register blueprints
    app.register_blueprint(about_bp, url_prefix="/about")
    app.register_blueprint(trp_admin, url_prefix="/trp-admin")

    @app.route("/")
    def home():
        return "Main page"

    return app

# tai basically:
# blueprintus sukuriu routuose (aka kituose microservices flasko 'about', 'clients' t.t.)
# init faile blueprint variables importinu is routes py failu, ir registerinu blueprint kad liktu create app funkcijoje
# na o per run.py, is init funkcijos importoju create_app funkcija, ir ja paleidziu.
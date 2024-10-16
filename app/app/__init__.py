# app/__init__.py

from flask import Flask
from config import Config
from extensions import db, migrate

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    # Initialize extensions
    db.init_app(app)
    migrate.init_app(app, db)

    # Import models and blueprints
    with app.app_context():
        from . import models
        from .routes import main_bp
        app.register_blueprint(main_bp)

    return app

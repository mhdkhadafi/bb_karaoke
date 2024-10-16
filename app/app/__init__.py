from flask import Flask
from .extensions import db, migrate
from .config import Config

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    # Initialize extensions
    db.init_app(app)
    migrate.init_app(app, db)

    # Import models and register blueprints/routes
    with app.app_context():
        from . import models
        from . import routes  # Your routes file

    return app
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from dotenv import load_dotenv
import os

# --- Load Environment Variables FIRST ---
load_dotenv() 

# --- Initialize Database Object ---
db = SQLAlchemy()

def create_app():
    """Create and configure an instance of the Flask application."""
    app = Flask(__name__)

    # --- CONFIGURATION ---
    app.config['SECRET_KEY'] = os.getenv("FLASK_SECRET_KEY")
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///../project.db' # Points to the db in the parent folder
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

    # --- Associate Database with the App ---
    db.init_app(app)

    # --- Import and Register Routes and Models ---
    with app.app_context():
        # Import routes and models here to avoid circular imports
        from . import routes
        from . import models

        # This command is not needed if you use the flask shell command
        # db.create_all()

        return app
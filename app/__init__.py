from flask import Flask
from flask_cors import CORS

from dotenv import load_dotenv
import os

# Create app
app = Flask(__name__)
# Get frontend URL from environment or default to localhost
frontend_url = os.getenv("FRONTEND_URL", "http://localhost:3000")
origins = [frontend_url]
if os.getenv("FLASK_ENV") == "development":
    origins.extend(["http://127.0.0.1:3000", "http://localhost:3000"])

CORS(app, resources={
    r"/*": {
        "origins": origins,
        "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
        "allow_headers": ["Content-Type", "Authorization"],
        "supports_credentials": True
    }
})
load_dotenv()
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv("DB", "sqlite:///database.db")
app.config['SECRET_KEY'] = os.getenv('SECRET', "testkey")
app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {
    "pool_pre_ping": True
}

# Init Database
from app.models import db

with app.app_context():
    db.create_all()

# Blueprints
from app.routes.auth import auth_bp
from app.routes.me import me_bp
from app.routes.vessels import vessel_bp
from app.routes.booking import booking_bp
from app.routes.ai_agent import ai_bp
from app.routes.admin import admin_bp

app.register_blueprint(auth_bp)
app.register_blueprint(me_bp)
app.register_blueprint(vessel_bp)
app.register_blueprint(booking_bp)
app.register_blueprint(ai_bp)
app.register_blueprint(admin_bp)
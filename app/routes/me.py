# All comments are made by a human. Not AI.

from flask import Blueprint, request, jsonify

from app import app
from app.models import db, Users
from app.decorators.token_required import token_required

# Create Me Blueprint
me_bp = Blueprint('me', __name__, url_prefix="/me")

# Routes
@me_bp.route("/get", methods=["GET"])
@token_required()
def get_profile(user):
    return jsonify({
        "success": True,
        "data": user.to_dict()
    }), 200 

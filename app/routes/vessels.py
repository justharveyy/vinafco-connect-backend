# This code is written by a human

from flask import Blueprint, request, jsonify

from app import app
from app.models import db, Vessels
from app.decorators.token_required import token_required

# Create Vessels Blueprint
vessel_bp = Blueprint('vessels', __name__, url_prefix="/vessels")

# Routes
@vessel_bp.route("/list", methods=["GET"])
@token_required()
def list_vessels(user):
    vessels = Vessels.query.all()
    vessel_list = []
    
    for vessel in vessels:
        vessel_list.append({
            "vessel_code": vessel.vessel_code,
            "vessel_name": vessel.vessel_name,
            "latest_status": vessel.latest_status,
            "speed": vessel.speed,
            "course": vessel.course,
            "true_heading": vessel.true_heading,
            "draught": vessel.draught,
            "reported_destination": vessel.reported_destination,
            "reported_eta": vessel.reported_eta.isoformat(),
            "matched_destination": vessel.matched_destination,
            "vessel_type": vessel.vessel_type,
            "last_updated": vessel.last_updated.isoformat()
        })
    return jsonify({
        "success": True,
        "data": vessel_list
    }), 200
    
@vessel_bp.route("/get/<vessel_code>", methods=["GET"])
@token_required()
def get_vessel(user, vessel_code):
    vessel = Vessels.query.filter_by(vessel_code=vessel_code).first()
    
    if not vessel:
        return jsonify({
            "success": False,
            "message": "Vessel not found"
        }), 404
    
    return jsonify({
        "success": True,
        "data": {
            "vessel_code": vessel.vessel_code,
            "vessel_name": vessel.vessel_name,
            "latest_status": vessel.latest_status,
            "speed": vessel.speed,
            "course": vessel.course,
            "true_heading": vessel.true_heading,
            "draught": vessel.draught,
            "reported_destination": vessel.reported_destination,
            "reported_eta": vessel.reported_eta.isoformat(),
            "matched_destination": vessel.matched_destination,
            "vessel_type": vessel.vessel_type,
            "last_updated": vessel.last_updated.isoformat()
        }
    }), 200
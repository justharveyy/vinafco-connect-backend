# This code is written by human

from flask import Blueprint, request, jsonify

from app import app
from app.models import (
    db,
    Users,
    Bookings,
    Payments,
    Vessels,
    Routes,
    Items,
    Confirmations,
)
from app.decorators.token_required import token_required
from app.helpers.generate_invoice import run

import requests
import random
from datetime import datetime, timedelta
import hashlib
import uuid


# Functions
def generate_booking_id():
    char = "QWERTYUIOPASDFGHJKLZXCVBNM1234567890"
    return "VFC-" + "".join(random.choice(char) for _ in range(8))


booking_bp = Blueprint("booking", __name__, url_prefix="/booking")

CARGO_TYPES = ["FCL/LCL", "REEFER", "DG/IMDG", "BULK", "RoRo"]

CARGO_MULTIPLER = {
    "FCL/LCL": {
        "multipler": 1.0,
        "description": "Full Container Load / Less than Container Load",
        "reason": "Standard cargo type with no special handling requirements.",
    },
    "REEFER": {
        "multipler": 1.3,
        "description": "Reefer Cargo",
        "reason": "Cargo that requires temperature control.",
    },
    "DG/IMDG": {
        "multipler": 1.5,
        "description": "Dangerous Goods / IMDG",
        "reason": "Cargo that is classified as dangerous and requires special handling.",
    },
    "BULK": {
        "multipler": 0.8,
        "description": "Bulk Cargo",
        "reason": "Cargo that is transported in large quantities without packaging.",
    },
    "RoRo": {
        "multipler": 1.3,
        "description": "Roll-on/Roll-off Cargo",
        "reason": "Cargo that is loaded and unloaded on vehicles or machinery.",
    },
}


@booking_bp.route("/estimate-quote", methods=["GET"])
@token_required()
def estimate_quote(user):
    vessel_code = request.args.get("vessel_code")
    route = request.args.get("route")
    cargo_type = request.args.get("cargo_type")
    weight = request.args.get("weight", type=float)

    # Validate first, query second
    if not vessel_code:
        return jsonify({"success": False, "message": "Vessel code is required"}), 400
    if not route or "-" not in route:
        return (
            jsonify(
                {
                    "success": False,
                    "message": "Route is required (format: FromPort-ToPort)",
                }
            ),
            400,
        )
    if cargo_type not in CARGO_TYPES:
        return (
            jsonify(
                {
                    "success": False,
                    "message": f"Invalid cargo type. Must be one of: {', '.join(CARGO_TYPES)}",
                }
            ),
            400,
        )

    vessel_obj = Vessels.query.filter_by(vessel_code=vessel_code).first()
    if not vessel_obj:
        return jsonify({"success": False, "message": "Vessel not found"}), 404

    route_parts = route.split("-")
    route_obj = Routes.query.filter_by(
        from_port=route_parts[0], to_port=route_parts[1], vessel_id=vessel_code
    ).first()
    if not route_obj:
        return (
            jsonify({"success": False, "message": "Invalid route for this vessel"}),
            400,
        )

    rate_per_kg = (
        route_obj.quote
        * route_obj.total_distance
        * CARGO_MULTIPLER[cargo_type]["multipler"]
    )
    estimated_total = round(rate_per_kg * weight, 2) if weight else None

    return jsonify(
        {
            "success": True,
            "data": {
                "from_port": route_obj.from_port,
                "to_port": route_obj.to_port,
                "vessel_code": vessel_code,
                "cargo_type": cargo_type,
                "rate_per_kg": round(rate_per_kg, 2),
                "estimated_total": estimated_total,  # only present if weight param passed
                "quote_breakdown": {
                    "base_quote": route_obj.quote,
                    "distance": route_obj.total_distance,
                    "cargo_type_multiplier": CARGO_MULTIPLER[cargo_type]["multipler"],
                    "reasoning": CARGO_MULTIPLER[cargo_type]["reason"],
                },
            },
        }
    )


@booking_bp.route("/create", methods=["POST"])
@token_required()
def create_booking(user):
    payload = request.get_json(silent=True)
    if not payload:
        return jsonify({"success": False, "message": "Invalid payload"}), 400

    vessel = payload.get("vessel_code", "").strip()
    route = payload.get("route", "").strip()
    cargo_type = payload.get("cargo_type", "").strip()

    if not route or "-" not in route:
        return (
            jsonify(
                {
                    "success": False,
                    "message": "Route is required (format: FromPort-ToPort)",
                }
            ),
            400,
        )
    if not vessel:
        return jsonify({"success": False, "message": "Vessel code is required"}), 400
    if cargo_type not in CARGO_TYPES:
        return (
            jsonify(
                {
                    "success": False,
                    "message": f"Invalid cargo type. Must be one of: {', '.join(CARGO_TYPES)}",
                }
            ),
            400,
        )

    route_parts = route.split("-")
    route_obj = Routes.query.filter_by(
        from_port=route_parts[0], to_port=route_parts[1], vessel_id=vessel
    ).first()
    if not route_obj:
        return jsonify({"success": False, "message": "Invalid route"}), 400

    vessel_obj = Vessels.query.filter_by(vessel_code=vessel).first()
    if not vessel_obj:
        return jsonify({"success": False, "message": "Invalid vessel code"}), 400

    items = payload.get("items", [])
    if not items:
        return (
            jsonify({"success": False, "message": "At least one item is required"}),
            400,
        )

    # Build booking shell
    booking = Bookings()
    booking.booking_id = generate_booking_id()
    booking.user_id = user.user_id
    booking.vessel_id = vessel
    booking.cargo_type = cargo_type
    booking.trip_length = route_obj.total_distance
    booking.booking_date = datetime.now()
    booking.estimated_start_time = datetime.now() + timedelta(days=7)
    booking.estimated_time_to_destination = booking.estimated_start_time + timedelta(
        hours=route_obj.total_distance / vessel_obj.speed
    )
    booking.expire_in = datetime.now() + timedelta(days=1)

    # Validate items + calculate
    item_objects = []
    total_weight = 0
    total_price = 0
    cargo_multiplier = CARGO_MULTIPLER[cargo_type]["multipler"]

    for item in items:
        name = item.get("name", "").strip()
        description = item.get("description", "").strip()
        weight = item.get("weight")

        if not name:
            return jsonify({"success": False, "message": "Item name is required"}), 400
        if not description:
            return (
                jsonify({"success": False, "message": "Item description is required"}),
                400,
            )
        if not isinstance(weight, (int, float)) or weight <= 0:
            return (
                jsonify(
                    {
                        "success": False,
                        "message": "Item weight must be a positive number",
                    }
                ),
                400,
            )

        item_price = (
            weight * route_obj.quote * route_obj.total_distance * cargo_multiplier
        )
        total_weight += weight
        total_price += item_price

        item_obj = Items()
        item_obj.booking_id = booking.booking_id
        item_obj.name = name
        item_obj.weight = weight
        item_obj.description = description
        item_obj.price = item_price
        item_objects.append(item_obj)

    base_price = (
        route_obj.quote * route_obj.total_distance
    )  # rate per kg, no multiplier
    extra_fee = total_price - (
        base_price * total_weight
    )  # total surcharge from cargo type

    booking.quote = route_obj.quote
    booking.extra_fees = extra_fee
    booking.total_package_weight = total_weight
    booking.total_price = total_price

    # Generate PDF + upload to Railway bucket
    result = run(
        {
            "booking_ref": booking.booking_id,
            "issue_date": datetime.now().strftime("%Y-%m-%d"),
            "customer": {
                "name": user.fullname,
                "address": user.address,
                "tax_id": user.tax_id or "N/A",
                "contact": user.fullname,
                "phone": user.phone_number or "N/A",
                "email": user.email,
            },
            "shipment": {
                "vessel": vessel_obj.vessel_name,
                "voyage": vessel_obj.call_sign,
                "pol": route_obj.from_port,
                "pod": route_obj.to_port,
                "etd": booking.estimated_start_time.strftime("%Y-%m-%d %H:%M"),
                "eta": booking.estimated_time_to_destination.strftime("%Y-%m-%d %H:%M"),
                "cargo_type": cargo_type,
                "quantity": len(items),
                "unit": "units",
                "description": f"{len(items)} item(s), {cargo_type}, {total_weight:,.0f} kg total",
                "gross_weight": f"{total_weight:,.0f} KG",
                "incoterm": cargo_type,
            },
            "charges": {
                "freight": f"{base_price * total_weight:,.0f}",
                "extra_fees": f"{extra_fee:,.0f}",
                "total": f"{total_price:,.0f}",
                "currency": "VND",
                "payment": "Prepaid",
            },
            "deadlines": {
                "booking_confirm": booking.expire_in.strftime("%Y-%m-%d %H:%M"),
                "customs": (booking.estimated_start_time - timedelta(days=4)).strftime(
                    "%Y-%m-%d %H:%M"
                ),
                "si_cutoff": (
                    booking.estimated_start_time - timedelta(days=3)
                ).strftime("%Y-%m-%d %H:%M"),
                "docs_cutoff": (
                    booking.estimated_start_time - timedelta(days=4)
                ).strftime("%Y-%m-%d %H:%M"),
                "cargo_cutoff": (
                    booking.estimated_start_time - timedelta(days=1)
                ).strftime("%Y-%m-%d %H:%M"),
            },
        }
    )

    # Confirmation record
    confirmation_id = str(uuid.uuid4())
    confirmation_key = uuid.uuid4().hex
    original_hash = result["original_hash"]
    signed_hash = hashlib.sha256(
        f"{original_hash}{confirmation_key}".encode()
    ).hexdigest()

    conf = Confirmations()
    conf.booking_id = booking.booking_id
    conf.confirmation_id = confirmation_id
    conf.confirmation_key = confirmation_key
    conf.recipient_phone_number = user.phone_number or ""
    conf.original_hash = original_hash
    conf.signed_hash = signed_hash

    try:
        db.session.add(booking)
        for item_obj in item_objects:
            db.session.add(item_obj)
        db.session.add(conf)
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        return jsonify({"success": False, "message": f"Database error: {str(e)}"}), 500

    return (
        jsonify(
            {
                "success": True,
                "message": "Booking created successfully",
                "data": {
                    "booking_id": booking.booking_id,
                    "total_price": total_price,
                    "total_weight": total_weight,
                    "estimated_departure": booking.estimated_start_time.isoformat(),
                    "estimated_arrival": booking.estimated_time_to_destination.isoformat(),
                    "expires_at": booking.expire_in.isoformat(),
                    "confirmation_id": confirmation_id,
                    "pdf_url": result.get("presigned_url"),
                },
            }
        ),
        201,
    )

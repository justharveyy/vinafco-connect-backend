from flask import Blueprint, request, jsonify
from app import app
from app.models import db, Vessels, Routes, UpcomingAvailability, Users, Bookings
from app.decorators.owner_required import owner_required
from datetime import datetime
import uuid

# Create Admin Blueprint
admin_bp = Blueprint('admin', __name__, url_prefix="/admin")

# ==================== VESSELS MANAGEMENT ====================

@admin_bp.route("/vessels", methods=["GET"])
@owner_required
def get_all_vessels(user):
    """Get all vessels for admin management"""
    vessels = Vessels.query.all()
    vessel_list = []
    
    for vessel in vessels:
        vessel_list.append({
            "id": vessel.id,
            "vessel_code": vessel.vessel_code,
            "vessel_name": vessel.vessel_name,
            "latest_status": vessel.latest_status,
            "speed": vessel.speed,
            "course": vessel.course,
            "true_heading": vessel.true_heading,
            "draught": vessel.draught,
            "reported_destination": vessel.reported_destination,
            "reported_eta": vessel.reported_eta.isoformat() if vessel.reported_eta else None,
            "matched_destination": vessel.matched_destination,
            "vessel_type": vessel.vessel_type,
            "last_updated": vessel.last_updated.isoformat() if vessel.last_updated else None,
            "flag": vessel.flag,
            "photo": vessel.photo,
            "call_sign": vessel.call_sign,
            "transponder_class": vessel.transponder_class,
            "mmsi_number": vessel.mmsi_number
        })
    
    return jsonify({
        "success": True,
        "data": vessel_list
    }), 200

@admin_bp.route("/vessels", methods=["POST"])
@owner_required
def create_vessel(user):
    """Create a new vessel"""
    data = request.get_json()
    
    # Validate required fields
    required_fields = ['vessel_code', 'vessel_name', 'vessel_type', 'flag', 'call_sign', 'transponder_class', 'mmsi_number']
    for field in required_fields:
        if field not in data or not data[field]:
            return jsonify({
                "success": False,
                "message": f"Field '{field}' is required"
            }), 400
    
    # Check if vessel code already exists
    existing_vessel = Vessels.query.filter_by(vessel_code=data['vessel_code']).first()
    if existing_vessel:
        return jsonify({
            "success": False,
            "message": "Vessel code already exists"
        }), 400
    
    # Create new vessel
    vessel = Vessels(
        vessel_code=data['vessel_code'],
        vessel_name=data['vessel_name'],
        latest_status=data.get('latest_status', 'Active'),
        speed=data.get('speed'),
        course=data.get('course'),
        true_heading=data.get('true_heading'),
        draught=data.get('draught'),
        reported_destination=data.get('reported_destination', ''),
        reported_eta=datetime.fromisoformat(data['reported_eta']) if data.get('reported_eta') else datetime.now(),
        matched_destination=data.get('matched_destination', ''),
        vessel_type=data['vessel_type'],
        last_updated=datetime.now(),
        flag=data['flag'],
        photo=data.get('photo', ''),
        call_sign=data['call_sign'],
        transponder_class=data['transponder_class'],
        mmsi_number=data['mmsi_number']
    )
    
    db.session.add(vessel)
    db.session.commit()
    
    return jsonify({
        "success": True,
        "message": "Vessel created successfully",
        "data": {
            "id": vessel.id,
            "vessel_code": vessel.vessel_code,
            "vessel_name": vessel.vessel_name
        }
    }), 201

@admin_bp.route("/vessels/<int:vessel_id>", methods=["PUT"])
@owner_required
def update_vessel(user, vessel_id):
    """Update an existing vessel"""
    vessel = Vessels.query.get(vessel_id)
    
    if not vessel:
        return jsonify({
            "success": False,
            "message": "Vessel not found"
        }), 404
    
    data = request.get_json()
    
    # Update vessel fields
    if 'vessel_name' in data:
        vessel.vessel_name = data['vessel_name']
    if 'latest_status' in data:
        vessel.latest_status = data['latest_status']
    if 'speed' in data:
        vessel.speed = data['speed']
    if 'course' in data:
        vessel.course = data['course']
    if 'true_heading' in data:
        vessel.true_heading = data['true_heading']
    if 'draught' in data:
        vessel.draught = data['draught']
    if 'reported_destination' in data:
        vessel.reported_destination = data['reported_destination']
    if 'reported_eta' in data:
        vessel.reported_eta = datetime.fromisoformat(data['reported_eta'])
    if 'matched_destination' in data:
        vessel.matched_destination = data['matched_destination']
    if 'vessel_type' in data:
        vessel.vessel_type = data['vessel_type']
    if 'flag' in data:
        vessel.flag = data['flag']
    if 'photo' in data:
        vessel.photo = data['photo']
    if 'call_sign' in data:
        vessel.call_sign = data['call_sign']
    if 'transponder_class' in data:
        vessel.transponder_class = data['transponder_class']
    if 'mmsi_number' in data:
        vessel.mmsi_number = data['mmsi_number']
    
    vessel.last_updated = datetime.now()
    db.session.commit()
    
    return jsonify({
        "success": True,
        "message": "Vessel updated successfully"
    }), 200

@admin_bp.route("/vessels/<int:vessel_id>", methods=["DELETE"])
@owner_required
def delete_vessel(user, vessel_id):
    """Delete a vessel"""
    vessel = Vessels.query.get(vessel_id)
    
    if not vessel:
        return jsonify({
            "success": False,
            "message": "Vessel not found"
        }), 404
    
    # Check if vessel has associated bookings or routes
    associated_routes = Routes.query.filter_by(vessel_id=vessel.vessel_code).count()
    associated_bookings = Bookings.query.filter_by(vessel_id=vessel.vessel_code).count()
    
    if associated_routes > 0 or associated_bookings > 0:
        return jsonify({
            "success": False,
            "message": "Cannot delete vessel with associated routes or bookings"
        }), 400
    
    db.session.delete(vessel)
    db.session.commit()
    
    return jsonify({
        "success": True,
        "message": "Vessel deleted successfully"
    }), 200

# ==================== ROUTES & QUOTES MANAGEMENT ====================

@admin_bp.route("/routes", methods=["GET"])
@owner_required
def get_all_routes(user):
    """Get all routes for admin management"""
    routes = Routes.query.all()
    route_list = []
    
    for route in routes:
        route_list.append({
            "id": route.id,
            "vessel_id": route.vessel_id,
            "quote_name": route.quote_name,
            "from_port": route.from_port,
            "from_port_code": route.from_port_code,
            "to_port": route.to_port,
            "to_port_code": route.to_port_code,
            "quote": route.quote,
            "total_distance": route.total_distance
        })
    
    return jsonify({
        "success": True,
        "data": route_list
    }), 200

@admin_bp.route("/routes", methods=["POST"])
@owner_required
def create_route(user):
    """Create a new route with quote"""
    data = request.get_json()
    
    # Validate required fields
    required_fields = ['vessel_id', 'quote_name', 'from_port', 'from_port_code', 'to_port', 'to_port_code', 'quote', 'total_distance']
    for field in required_fields:
        if field not in data or data[field] is None:
            return jsonify({
                "success": False,
                "message": f"Field '{field}' is required"
            }), 400
    
    # Check if vessel exists
    vessel = Vessels.query.filter_by(vessel_code=data['vessel_id']).first()
    if not vessel:
        return jsonify({
            "success": False,
            "message": "Vessel not found"
        }), 404
    
    # Create new route
    route = Routes(
        vessel_id=data['vessel_id'],
        quote_name=data['quote_name'],
        from_port=data['from_port'],
        from_port_code=data['from_port_code'],
        to_port=data['to_port'],
        to_port_code=data['to_port_code'],
        quote=float(data['quote']),
        total_distance=float(data['total_distance'])
    )
    
    db.session.add(route)
    db.session.commit()
    
    return jsonify({
        "success": True,
        "message": "Route created successfully",
        "data": {
            "id": route.id,
            "quote_name": route.quote_name
        }
    }), 201

@admin_bp.route("/routes/<int:route_id>", methods=["PUT"])
@owner_required
def update_route(user, route_id):
    """Update an existing route"""
    route = Routes.query.get(route_id)
    
    if not route:
        return jsonify({
            "success": False,
            "message": "Route not found"
        }), 404
    
    data = request.get_json()
    
    # Update route fields
    if 'quote_name' in data:
        route.quote_name = data['quote_name']
    if 'from_port' in data:
        route.from_port = data['from_port']
    if 'from_port_code' in data:
        route.from_port_code = data['from_port_code']
    if 'to_port' in data:
        route.to_port = data['to_port']
    if 'to_port_code' in data:
        route.to_port_code = data['to_port_code']
    if 'quote' in data:
        route.quote = float(data['quote'])
    if 'total_distance' in data:
        route.total_distance = float(data['total_distance'])
    if 'vessel_id' in data:
        # Check if new vessel exists
        vessel = Vessels.query.filter_by(vessel_code=data['vessel_id']).first()
        if not vessel:
            return jsonify({
                "success": False,
                "message": "Vessel not found"
            }), 404
        route.vessel_id = data['vessel_id']
    
    db.session.commit()
    
    return jsonify({
        "success": True,
        "message": "Route updated successfully"
    }), 200

@admin_bp.route("/routes/<int:route_id>", methods=["DELETE"])
@owner_required
def delete_route(user, route_id):
    """Delete a route"""
    route = Routes.query.get(route_id)
    
    if not route:
        return jsonify({
            "success": False,
            "message": "Route not found"
        }), 404
    
    db.session.delete(route)
    db.session.commit()
    
    return jsonify({
        "success": True,
        "message": "Route deleted successfully"
    }), 200

# ==================== SCHEDULES MANAGEMENT ====================

@admin_bp.route("/schedules", methods=["GET"])
@owner_required
def get_all_schedules(user):
    """Get all vessel schedules/availability"""
    schedules = UpcomingAvailability.query.all()
    schedule_list = []
    
    for schedule in schedules:
        schedule_list.append({
            "id": schedule.id,
            "vessel_id": schedule.vessel_id,
            "available_weight": schedule.available_weight,
            "remaining_weight": schedule.remaining_weight,
            "departure_date_time": schedule.departure_date_time,
            "arrival_date_time": schedule.arrival_date_time,
            "depart_from": schedule.depart_from,
            "depart_from_port_code": schedule.depart_from_port_code,
            "arrive_to": schedule.arrive_to,
            "arrive_to_port_code": schedule.arrive_to_port_code,
            "last_updated": schedule.last_updated.isoformat() if schedule.last_updated else None
        })
    
    return jsonify({
        "success": True,
        "data": schedule_list
    }), 200

@admin_bp.route("/schedules", methods=["POST"])
@owner_required
def create_schedule(user):
    """Create a new vessel schedule"""
    data = request.get_json()
    
    # Validate required fields
    required_fields = ['vessel_id', 'available_weight', 'remaining_weight', 'departure_date_time', 
                      'arrival_date_time', 'depart_from', 'depart_from_port_code', 'arrive_to', 'arrive_to_port_code']
    for field in required_fields:
        if field not in data or data[field] is None:
            return jsonify({
                "success": False,
                "message": f"Field '{field}' is required"
            }), 400
    
    # Check if vessel exists
    vessel = Vessels.query.filter_by(vessel_code=data['vessel_id']).first()
    if not vessel:
        return jsonify({
            "success": False,
            "message": "Vessel not found"
        }), 404
    
    # Create new schedule
    schedule = UpcomingAvailability(
        vessel_id=data['vessel_id'],
        available_weight=float(data['available_weight']),
        remaining_weight=float(data['remaining_weight']),
        departure_date_time=float(data['departure_date_time']),
        arrival_date_time=float(data['arrival_date_time']),
        depart_from=data['depart_from'],
        depart_from_port_code=data['depart_from_port_code'],
        arrive_to=data['arrive_to'],
        arrive_to_port_code=data['arrive_to_port_code'],
        last_updated=datetime.now()
    )
    
    db.session.add(schedule)
    db.session.commit()
    
    return jsonify({
        "success": True,
        "message": "Schedule created successfully",
        "data": {
            "id": schedule.id,
            "vessel_id": schedule.vessel_id
        }
    }), 201

@admin_bp.route("/schedules/<int:schedule_id>", methods=["PUT"])
@owner_required
def update_schedule(user, schedule_id):
    """Update an existing schedule"""
    schedule = UpcomingAvailability.query.get(schedule_id)
    
    if not schedule:
        return jsonify({
            "success": False,
            "message": "Schedule not found"
        }), 404
    
    data = request.get_json()
    
    # Update schedule fields
    if 'available_weight' in data:
        schedule.available_weight = float(data['available_weight'])
    if 'remaining_weight' in data:
        schedule.remaining_weight = float(data['remaining_weight'])
    if 'departure_date_time' in data:
        schedule.departure_date_time = float(data['departure_date_time'])
    if 'arrival_date_time' in data:
        schedule.arrival_date_time = float(data['arrival_date_time'])
    if 'depart_from' in data:
        schedule.depart_from = data['depart_from']
    if 'depart_from_port_code' in data:
        schedule.depart_from_port_code = data['depart_from_port_code']
    if 'arrive_to' in data:
        schedule.arrive_to = data['arrive_to']
    if 'arrive_to_port_code' in data:
        schedule.arrive_to_port_code = data['arrive_to_port_code']
    if 'vessel_id' in data:
        # Check if new vessel exists
        vessel = Vessels.query.filter_by(vessel_code=data['vessel_id']).first()
        if not vessel:
            return jsonify({
                "success": False,
                "message": "Vessel not found"
            }), 404
        schedule.vessel_id = data['vessel_id']
    
    schedule.last_updated = datetime.now()
    db.session.commit()
    
    return jsonify({
        "success": True,
        "message": "Schedule updated successfully"
    }), 200

@admin_bp.route("/schedules/<int:schedule_id>", methods=["DELETE"])
@owner_required
def delete_schedule(user, schedule_id):
    """Delete a schedule"""
    schedule = UpcomingAvailability.query.get(schedule_id)
    
    if not schedule:
        return jsonify({
            "success": False,
            "message": "Schedule not found"
        }), 404
    
    db.session.delete(schedule)
    db.session.commit()
    
    return jsonify({
        "success": True,
        "message": "Schedule deleted successfully"
    }), 200

# ==================== USER MANAGEMENT ====================

@admin_bp.route("/users", methods=["GET"])
@owner_required
def get_all_users(user):
    """Get all users for admin management"""
    users = Users.query.all()
    user_list = []
    
    for user_data in users:
        user_list.append({
            "id": user_data.id,
            "user_id": user_data.user_id,
            "fullname": user_data.fullname,
            "email": user_data.email,
            "phone_number": user_data.phone_number,
            "phone_number_verified": user_data.phone_number_verified,
            "is_customer": user_data.is_customer,
            "balance": user_data.balance,
            "email_verified": user_data.email_verified,
            "role": user_data.role,
            "created_at": user_data.created_at.isoformat() if user_data.created_at else None,
            "address": user_data.address,
            "tax_id": user_data.tax_id
        })
    
    return jsonify({
        "success": True,
        "data": user_list
    }), 200

@admin_bp.route("/users/<string:user_id>/role", methods=["PUT"])
@owner_required
def update_user_role(user, user_id):
    """Update a user's role"""
    target_user = Users.query.filter_by(user_id=user_id).first()
    
    if not target_user:
        return jsonify({
            "success": False,
            "message": "User not found"
        }), 404
    
    data = request.get_json()
    
    if 'role' not in data or data['role'] not in ['User', 'Admin', 'Owner']:
        return jsonify({
            "success": False,
            "message": "Invalid role. Must be 'User', 'Admin', or 'Owner'"
        }), 400
    
    target_user.role = data['role']
    db.session.commit()
    
    return jsonify({
        "success": True,
        "message": "User role updated successfully"
    }), 200

# ==================== BOOKINGS MANAGEMENT ====================

@admin_bp.route("/bookings", methods=["GET"])
@owner_required
def get_all_bookings(user):
    """Get all bookings for admin management"""
    bookings = Bookings.query.all()
    booking_list = []
    
    for booking in bookings:
        booking_list.append({
            "id": booking.id,
            "booking_id": booking.booking_id,
            "user_id": booking.user_id,
            "vessel_id": booking.vessel_id,
            "booking_date": booking.booking_date.isoformat() if booking.booking_date else None,
            "quote": booking.quote,
            "extra_fees": booking.extra_fees,
            "total_price": booking.total_price,
            "total_package_weight": booking.total_package_weight,
            "trip_length": booking.trip_length,
            "estimated_start_time": booking.estimated_start_time.isoformat() if booking.estimated_start_time else None,
            "estimated_time_to_destination": booking.estimated_time_to_destination.isoformat() if booking.estimated_time_to_destination else None,
            "status": booking.status,
            "expire_in": booking.expire_in.isoformat() if booking.expire_in else None,
            "cargo_type": booking.cargo_type
        })
    
    return jsonify({
        "success": True,
        "data": booking_list
    }), 200

@admin_bp.route("/bookings/<string:booking_id>/status", methods=["PUT"])
@owner_required
def update_booking_status(user, booking_id):
    """Update booking status"""
    booking = Bookings.query.filter_by(booking_id=booking_id).first()
    
    if not booking:
        return jsonify({
            "success": False,
            "message": "Booking not found"
        }), 404
    
    data = request.get_json()
    
    if 'status' not in data:
        return jsonify({
            "success": False,
            "message": "Status field is required"
        }), 400
    
    valid_statuses = ['Requested', 'Confirmed', 'In Transit', 'Completed', 'Cancelled']
    if data['status'] not in valid_statuses:
        return jsonify({
            "success": False,
            "message": f"Invalid status. Must be one of: {', '.join(valid_statuses)}"
        }), 400
    
    booking.status = data['status']
    db.session.commit()
    
    return jsonify({
        "success": True,
        "message": "Booking status updated successfully"
    }), 200

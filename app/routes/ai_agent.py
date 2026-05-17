# This code is written by a human

from flask import Blueprint, request, jsonify, Response, stream_with_context, current_app
from openai import OpenAI
import json
import os
import logging
import traceback
import uuid
import hashlib
from datetime import datetime, timedelta

from app.decorators.token_required import token_required
from app.models import db, Vessels, Routes, Bookings, Items, Confirmations, Users, UpcomingAvailability
from app.routes.booking import generate_booking_id, CARGO_TYPES, CARGO_MULTIPLER
from app.helpers.generate_invoice import run as generate_invoice

# Setup logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

ai_bp = Blueprint("ai", __name__, url_prefix="/ai")

# Initialize OpenAI client
api_key = os.getenv("OPENAI_API_KEY")
logger.debug(f"OpenAI API Key present: {bool(api_key)}")
if not api_key:
    logger.error("OPENAI_API_KEY not set in environment!")
client = OpenAI(api_key=api_key)

# System prompt for the AI assistant
SYSTEM_PROMPT = """You are the Vinafco AI Booking Assistant. You help customers of Vinafco Shipping JSC book cargo space on Vietnamese coastal container vessels. You can look up vessels, check availability, calculate quotes, and submit bookings on behalf of the user.

You are professional but approachable. You understand Vietnamese shipping logistics. You always confirm costs and details with the user before submitting any booking.

---

## The Company
**Vinafco Shipping JSC (VINAFCO)**
- Address: Tu Khoat Village, Thanh Tri, Ha Noi
- Phone: 1900 255 516 | Email: info@vinafco.com.vn

## The Fleet
- **Morning Vinafco** — vessel_code: `VFC-MV`, DWT 8,721t, bookable ~6,977t, speed 8.2 kn
- **Vinafco 26** — vessel_code: `VFC-26`, DWT 7,200t, bookable ~5,760t, speed 8.3 kn

## Routes
Both vessels operate: Ho Chi Minh City ↔ Hai Phong (1,150 km)
- Route string format: `FromPort-ToPort` e.g. `Hai Phong-Ho Chi Minh City` or `Ho Chi Minh City-Hai Phong`
- Transit: ~140h (Morning Vinafco) / ~138.5h (Vinafco 26)

## Pricing
- Base: **7.75 VND/kg/km** on this route
- rate_per_kg = 7.75 × 1,150 × cargo_multiplier

| Cargo Type | API Value | Multiplier | Rate/kg |
|---|---|---|---|
| Standard Container | FCL/LCL | 1.0× | 8,912 VND/kg |
| Reefer | REEFER | 1.3× | 11,586 VND/kg |
| Dangerous Goods | DG/IMDG | 1.5× | 13,369 VND/kg |
| Bulk | BULK | 0.8× | 7,130 VND/kg |
| Roll-on/Roll-off | RoRo | 1.3× | 11,586 VND/kg |

## AUTO-DETECT CARGO TYPE from user descriptions:
- **FCL/LCL**: containers, boxes, pallets, general cargo, manufactured goods, electronics, furniture
- **REEFER**: frozen, chilled, cold, temperature-controlled, perishable, food, seafood, meat, dairy, flowers
- **DG/IMDG**: chemicals, hazardous, dangerous goods, flammable, toxic, explosives, batteries, fuel, paint, gas
- **BULK**: grain, coal, ore, oil, sand, cement, wheat, rice, sugar, minerals, liquids in bulk
- **RoRo**: cars, trucks, vehicles, buses, trailers, machinery with wheels, heavy equipment, automobiles

## Booking Rules
1. At least 7 days lead time required
2. Booking expires in 24 hours if not paid
3. At least one item required (name, description, weight in kg > 0)
4. Currency: VND | Payment: Prepaid
5. **NEVER submit a booking without explicit user confirmation**

## Booking Flow
1. Ask: which vessel? (suggest based on availability if needed)
2. Ask: which route? (northbound or southbound)
3. Ask: cargo type?
4. Ask: what items? (name, description, weight for each — NEVER assume weight)
5. Call `calculate_quote` with total weight → show price breakdown
6. Show full summary (vessel, route, items, total in VND), ask "Shall I confirm this booking?"
7. Only on explicit confirmation → call `create_booking`
8. Return booking ID, PDF URL, expiry time

## Error handling
- 400: Tell user what's wrong, ask to correct
- 401/403: Tell user session expired, ask to log in again
- 404: Vessel/route not found, suggest alternatives
- 500: Apologise, ask user to try again

## Rules
- NEVER invent vessel codes, route names, or port names — only use VFC-MV and VFC-26, and the two port names above
- NEVER quote a final price without calling calculate_quote first (use formula only for estimates during conversation)
- NEVER tell the user the booking is confirmed until the API returns success: true
- NEVER assume cargo weight — always ask explicitly
- Format all VND amounts as ₫1,234,000 or 1,234,000 VND (no decimals)
- Format weights in kg, distances in km
"""

# Function definitions for OpenAI function calling
TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "list_vessels",
            "description": "Get a list of all available vessels with their basic information",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_vessel_details",
            "description": "Get detailed information about a specific vessel by its vessel code",
            "parameters": {
                "type": "object",
                "properties": {
                    "vessel_code": {
                        "type": "string",
                        "description": "The unique vessel code (e.g., VFC-001)"
                    }
                },
                "required": ["vessel_code"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "calculate_quote",
            "description": "Calculate a shipping quote based on vessel, route, cargo type, and weight",
            "parameters": {
                "type": "object",
                "properties": {
                    "vessel_code": {
                        "type": "string",
                        "description": "The vessel code to use for the quote"
                    },
                    "route": {
                        "type": "string",
                        "description": "The route in format 'FromPort-ToPort' (e.g., 'Hai Phong-Ho Chi Minh City')"
                    },
                    "cargo_type": {
                        "type": "string",
                        "enum": ["FCL/LCL", "REEFER", "DG/IMDG", "BULK", "RoRo"],
                        "description": "The type of cargo"
                    },
                    "weight": {
                        "type": "number",
                        "description": "Total weight in kg (optional for rate per kg only)"
                    }
                },
                "required": ["vessel_code", "route", "cargo_type"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_cargo_types_info",
            "description": "Get information about available cargo types and their pricing multipliers",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "create_booking",
            "description": "Create a shipping booking. Use this ONLY after the user has explicitly confirmed all details.",
            "parameters": {
                "type": "object",
                "properties": {
                    "vessel_code": {
                        "type": "string",
                        "description": "The vessel code for the booking (VFC-MV or VFC-26)"
                    },
                    "route": {
                        "type": "string",
                        "description": "Route in format 'FromPort-ToPort' e.g. 'Hai Phong-Ho Chi Minh City'"
                    },
                    "cargo_type": {
                        "type": "string",
                        "enum": ["FCL/LCL", "REEFER", "DG/IMDG", "BULK", "RoRo"],
                        "description": "Cargo type"
                    },
                    "items": {
                        "type": "array",
                        "description": "List of items to ship",
                        "items": {
                            "type": "object",
                            "properties": {
                                "name": {"type": "string", "description": "Item name"},
                                "description": {"type": "string", "description": "Item description"},
                                "weight": {"type": "number", "description": "Weight in kg"}
                            },
                            "required": ["name", "description", "weight"]
                        }
                    }
                },
                "required": ["vessel_code", "route", "cargo_type", "items"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "check_availability",
            "description": "Check upcoming sailing availability for a vessel and route. Returns slots with remaining cargo capacity.",
            "parameters": {
                "type": "object",
                "properties": {
                    "vessel_code": {
                        "type": "string",
                        "description": "Vessel code to check (VFC-MV or VFC-26). Omit to check all vessels."
                    },
                    "depart_from": {
                        "type": "string",
                        "description": "Departure port name e.g. 'Hai Phong' or 'Ho Chi Minh City'"
                    },
                    "min_weight": {
                        "type": "number",
                        "description": "Minimum remaining weight capacity needed in kg"
                    }
                },
                "required": []
            }
        }
    }
]


def list_vessels():
    """Get all vessels"""
    vessels = Vessels.query.all()
    return {
        "success": True,
        "vessels": [
            {
                "vessel_code": v.vessel_code,
                "vessel_name": v.vessel_name,
                "latest_status": v.latest_status,
                "vessel_type": v.vessel_type,
                "reported_destination": v.reported_destination,
                "speed": v.speed,
                "flag": v.flag
            }
            for v in vessels
        ]
    }


def get_vessel_details(vessel_code):
    """Get vessel details"""
    vessel = Vessels.query.filter_by(vessel_code=vessel_code).first()
    if not vessel:
        return {"success": False, "message": f"Vessel {vessel_code} not found"}
    
    # Get routes for this vessel
    routes = Routes.query.filter_by(vessel_id=vessel_code).all()
    
    return {
        "success": True,
        "vessel": {
            "vessel_code": vessel.vessel_code,
            "vessel_name": vessel.vessel_name,
            "latest_status": vessel.latest_status,
            "speed": vessel.speed,
            "course": vessel.course,
            "true_heading": vessel.true_heading,
            "draught": vessel.draught,
            "reported_destination": vessel.reported_destination,
            "vessel_type": vessel.vessel_type,
            "flag": vessel.flag,
            "call_sign": vessel.call_sign,
            "mmsi_number": vessel.mmsi_number
        },
        "available_routes": [
            {
                "from_port": r.from_port,
                "to_port": r.to_port,
                "quote": r.quote,
                "distance": r.total_distance
            }
            for r in routes
        ]
    }


def _split_route(route):
    """Split a route string on the first '-' to handle port names like 'Ho Chi Minh City'"""
    idx = route.find("-")
    if idx == -1:
        return None, None
    return route[:idx], route[idx + 1:]


def check_availability(vessel_code=None, depart_from=None, min_weight=None):
    """Check upcoming sailing availability"""
    import time
    now_ts = time.time()
    lead_ts = now_ts + (7 * 24 * 3600)

    query = UpcomingAvailability.query.filter(
        UpcomingAvailability.departure_date_time >= lead_ts
    )
    if vessel_code:
        query = query.filter(UpcomingAvailability.vessel_id == vessel_code)
    if depart_from:
        query = query.filter(UpcomingAvailability.depart_from == depart_from)
    if min_weight:
        query = query.filter(UpcomingAvailability.remaining_weight >= min_weight)

    slots = query.order_by(UpcomingAvailability.departure_date_time).limit(10).all()

    return {
        "success": True,
        "slots": [
            {
                "vessel_id": s.vessel_id,
                "depart_from": s.depart_from,
                "arrive_to": s.arrive_to,
                "departure_date_time": s.departure_date_time,
                "arrival_date_time": s.arrival_date_time,
                "available_weight_kg": s.available_weight,
                "remaining_weight_kg": s.remaining_weight,
            }
            for s in slots
        ]
    }


def calculate_quote(vessel_code, route, cargo_type, weight=None):
    """Calculate shipping quote"""
    if cargo_type not in CARGO_TYPES:
        return {
            "success": False,
            "message": f"Invalid cargo type. Must be one of: {', '.join(CARGO_TYPES)}"
        }

    from_port, to_port = _split_route(route)
    if not from_port or not to_port:
        return {
            "success": False,
            "message": "Route must be in format 'FromPort-ToPort'"
        }

    route_obj = Routes.query.filter_by(
        from_port=from_port, to_port=to_port, vessel_id=vessel_code
    ).first()
    
    if not route_obj:
        return {
            "success": False,
            "message": f"Route {route} not available for vessel {vessel_code}"
        }
    
    rate_per_kg = route_obj.quote * route_obj.total_distance * CARGO_MULTIPLER[cargo_type]["multipler"]
    
    result = {
        "success": True,
        "quote": {
            "vessel_code": vessel_code,
            "vessel_name": route_obj.quote_name,
            "route": route,
            "from_port": route_obj.from_port,
            "to_port": route_obj.to_port,
            "cargo_type": cargo_type,
            "cargo_description": CARGO_MULTIPLER[cargo_type]["description"],
            "rate_per_kg": round(rate_per_kg, 2),
            "distance_km": route_obj.total_distance,
            "base_quote": route_obj.quote,
            "cargo_multiplier": CARGO_MULTIPLER[cargo_type]["multipler"],
            "multiplier_reason": CARGO_MULTIPLER[cargo_type]["reason"]
        }
    }
    
    if weight:
        result["quote"]["total_weight"] = weight
        result["quote"]["estimated_total"] = round(rate_per_kg * weight, 2)
    
    return result


def get_cargo_types_info():
    """Get cargo types information"""
    return {
        "success": True,
        "cargo_types": CARGO_MULTIPLER
    }


def create_booking_for_user(user_id, vessel_code, route, cargo_type, items):
    """Create a booking for a user — mirrors booking.py logic exactly"""
    user = Users.query.filter_by(user_id=user_id).first()
    if not user:
        return {"success": False, "message": "User not found"}

    from_port, to_port = _split_route(route)
    if not from_port or not to_port:
        return {"success": False, "message": "Route must be in format 'FromPort-ToPort'"}

    route_obj = Routes.query.filter_by(
        from_port=from_port, to_port=to_port, vessel_id=vessel_code
    ).first()
    if not route_obj:
        return {"success": False, "message": f"Route {route} not available for vessel {vessel_code}"}

    vessel_obj = Vessels.query.filter_by(vessel_code=vessel_code).first()
    if not vessel_obj:
        return {"success": False, "message": f"Vessel {vessel_code} not found"}

    if not items or len(items) == 0:
        return {"success": False, "message": "At least one item is required"}

    for item in items:
        if not item.get("name") or not item.get("description"):
            return {"success": False, "message": "Each item must have a name and description"}
        if not isinstance(item.get("weight"), (int, float)) or item["weight"] <= 0:
            return {"success": False, "message": "Item weight must be a positive number"}

    cargo_multiplier = CARGO_MULTIPLER[cargo_type]["multipler"]
    now = datetime.now()
    booking = Bookings()
    booking.booking_id = generate_booking_id()
    booking.user_id = user_id
    booking.vessel_id = vessel_code
    booking.cargo_type = cargo_type
    booking.trip_length = route_obj.total_distance
    booking.booking_date = now
    booking.estimated_start_time = now + timedelta(days=7)
    booking.estimated_time_to_destination = booking.estimated_start_time + timedelta(
        hours=route_obj.total_distance / vessel_obj.speed
    )
    booking.expire_in = now + timedelta(days=1)

    item_objects = []
    total_weight = 0
    total_price = 0

    for item in items:
        item_price = item["weight"] * route_obj.quote * route_obj.total_distance * cargo_multiplier
        total_weight += item["weight"]
        total_price += item_price

        item_obj = Items()
        item_obj.booking_id = booking.booking_id
        item_obj.name = item["name"]
        item_obj.weight = item["weight"]
        item_obj.description = item["description"]
        item_obj.price = item_price
        item_objects.append(item_obj)

    base_price = route_obj.quote * route_obj.total_distance
    extra_fee = total_price - (base_price * total_weight)

    booking.quote = route_obj.quote
    booking.extra_fees = extra_fee
    booking.total_package_weight = total_weight
    booking.total_price = total_price

    result = generate_invoice(
        {
            "booking_ref": booking.booking_id,
            "issue_date": now.strftime("%Y-%m-%d"),
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
                "customs": (booking.estimated_start_time - timedelta(days=4)).strftime("%Y-%m-%d %H:%M"),
                "si_cutoff": (booking.estimated_start_time - timedelta(days=3)).strftime("%Y-%m-%d %H:%M"),
                "docs_cutoff": (booking.estimated_start_time - timedelta(days=4)).strftime("%Y-%m-%d %H:%M"),
                "cargo_cutoff": (booking.estimated_start_time - timedelta(days=1)).strftime("%Y-%m-%d %H:%M"),
            },
        }
    )

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

        return {
            "success": True,
            "data": {
                "booking_id": booking.booking_id,
                "vessel_code": vessel_code,
                "vessel_name": vessel_obj.vessel_name,
                "route": route,
                "cargo_type": cargo_type,
                "total_weight": total_weight,
                "total_price": round(total_price, 2),
                "base_price": round(base_price * total_weight, 2),
                "extra_fees": round(extra_fee, 2),
                "status": "Requested",
                "estimated_departure": booking.estimated_start_time.isoformat(),
                "estimated_arrival": booking.estimated_time_to_destination.isoformat(),
                "expires_at": booking.expire_in.isoformat(),
                "confirmation_id": confirmation_id,
                "pdf_url": result.get("presigned_url"),
                "items_count": len(items),
            }
        }
    except Exception as e:
        db.session.rollback()
        return {"success": False, "message": f"Database error: {str(e)}"}


def execute_function(function_name, arguments, user=None):
    """Execute the appropriate function based on name and arguments"""
    if function_name == "list_vessels":
        return list_vessels()
    elif function_name == "get_vessel_details":
        return get_vessel_details(arguments.get("vessel_code"))
    elif function_name == "calculate_quote":
        return calculate_quote(
            arguments.get("vessel_code"),
            arguments.get("route"),
            arguments.get("cargo_type"),
            arguments.get("weight")
        )
    elif function_name == "get_cargo_types_info":
        return get_cargo_types_info()
    elif function_name == "check_availability":
        return check_availability(
            vessel_code=arguments.get("vessel_code"),
            depart_from=arguments.get("depart_from"),
            min_weight=arguments.get("min_weight")
        )
    elif function_name == "create_booking":
        if user is None:
            return {"success": False, "message": "create_booking requires user context"}
        return create_booking_for_user(
            user.user_id,
            arguments.get("vessel_code"),
            arguments.get("route"),
            arguments.get("cargo_type"),
            arguments.get("items", [])
        )
    else:
        return {"success": False, "message": f"Unknown function: {function_name}"}


@ai_bp.route("/chat", methods=["POST"])
@token_required()
def chat(user):
    """Non-streaming chat endpoint"""
    logger.info(f"[AI Chat] Request from user: {user.user_id}")
    
    data = request.get_json()
    logger.debug(f"[AI Chat] Request data: {data}")
    
    if not data or "messages" not in data:
        logger.warning("[AI Chat] Missing messages in request")
        return jsonify({"success": False, "message": "Messages required"}), 400
    
    messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    messages.extend(data["messages"])
    
    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=messages,
            tools=TOOLS,
            tool_choice="auto",
            max_tokens=1000
        )
        
        assistant_message = response.choices[0].message
        
        # Check if tool calls are needed
        if assistant_message.tool_calls:
            # Add assistant message with tool calls
            messages.append({
                "role": "assistant",
                "content": assistant_message.content or "",
                "tool_calls": [
                    {
                        "id": tc.id,
                        "type": "function",
                        "function": {
                            "name": tc.function.name,
                            "arguments": tc.function.arguments
                        }
                    }
                    for tc in assistant_message.tool_calls
                ]
            })
            
            # Execute tool calls
            for tool_call in assistant_message.tool_calls:
                function_name = tool_call.function.name
                arguments = json.loads(tool_call.function.arguments)
                result = execute_function(function_name, arguments, user=user)
                
                # Add tool result to messages
                messages.append({
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "content": json.dumps(result)
                })
            
            # Get final response from model
            final_response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=messages,
                max_tokens=2000
            )
            
            return jsonify({
                "success": True,
                "response": final_response.choices[0].message.content,
                "tool_calls_executed": len(assistant_message.tool_calls)
            })
        
        return jsonify({
            "success": True,
            "response": assistant_message.content
        })
        
    except Exception as e:
        stack_trace = traceback.format_exc()
        logger.exception(f"[AI Chat] Error: {str(e)}")
        return jsonify({
            "success": False,
            "message": str(e),
            "error_type": type(e).__name__,
            "stack_trace": stack_trace
        }), 500


@ai_bp.route("/chat/stream", methods=["POST"])
@token_required()
def chat_stream(user):
    """Streaming chat endpoint using Server-Sent Events"""
    logger.info(f"[AI Stream] Request from user: {user.user_id}")
    
    data = request.get_json()
    logger.debug(f"[AI Stream] Request data: {data}")
    
    if not data or "messages" not in data:
        logger.warning("[AI Stream] Missing messages in request")
        return jsonify({"success": False, "message": "Messages required"}), 400
    
    messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    messages.extend(data["messages"])
    logger.debug(f"[AI Stream] Total messages: {len(messages)}")
    
    def generate():
        try:
            logger.info("[AI Stream] Starting OpenAI stream request")
            # First completion - may include tool calls
            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=messages,
                tools=TOOLS,
                tool_choice="auto",
                max_tokens=1000,
                stream=True
            )
            logger.info("[AI Stream] OpenAI stream started successfully")
            
            tool_calls_buffer = []
            current_tool_call = None
            content_buffer = ""
            
            for chunk in response:
                delta = chunk.choices[0].delta
                
                # Stream content if present
                if delta.content:
                    content_buffer += delta.content
                    yield f"data: {json.dumps({'type': 'content', 'content': delta.content})}\n\n"
                
                # Collect tool calls
                if delta.tool_calls:
                    for tc in delta.tool_calls:
                        if tc.index is not None and tc.index >= len(tool_calls_buffer):
                            tool_calls_buffer.append({
                                "id": tc.id or "",
                                "function": {"name": tc.function.name or "", "arguments": tc.function.arguments or ""},
                                "type": "function"
                            })
                        elif tc.function:
                            if tc.function.name:
                                tool_calls_buffer[tc.index]["function"]["name"] += tc.function.name
                            if tc.function.arguments:
                                tool_calls_buffer[tc.index]["function"]["arguments"] += tc.function.arguments
            
            logger.debug(f"[AI Stream] Content buffer: {content_buffer[:100]}...")
            logger.info(f"[AI Stream] Tool calls collected: {len(tool_calls_buffer)}")
            
            # If there are tool calls, execute them and get final response
            if tool_calls_buffer:
                logger.info("[AI Stream] Executing tool calls")
                yield f"data: {json.dumps({'type': 'status', 'content': 'Processing your request...'})}\n\n"
                
                # Add assistant message with tool calls
                messages.append({
                    "role": "assistant",
                    "content": content_buffer,
                    "tool_calls": tool_calls_buffer
                })
                
                # Execute tool calls
                for tool_call in tool_calls_buffer:
                    function_name = tool_call["function"]["name"]
                    try:
                        arguments = json.loads(tool_call["function"]["arguments"])
                    except:
                        arguments = {}
                    
                    logger.info(f"[AI Stream] Executing function: {function_name} with args: {arguments}")
                    
                    result = execute_function(function_name, arguments, user=user)
                    
                    logger.debug(f"[AI Stream] Function {function_name} result: {result}")
                    
                    # Add tool result
                    messages.append({
                        "role": "tool",
                        "tool_call_id": tool_call["id"],
                        "content": json.dumps(result)
                    })
                    
                    # Notify about tool execution
                    yield f"data: {json.dumps({'type': 'tool_call', 'function': function_name, 'result': result})}\n\n"
                
                # Stream final response
                final_response = client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=messages,
                    max_tokens=1000,
                    stream=True
                )
                
                for chunk in final_response:
                    if chunk.choices[0].delta.content:
                        yield f"data: {json.dumps({'type': 'content', 'content': chunk.choices[0].delta.content})}\n\n"
            
            yield f"data: {json.dumps({'type': 'done'})}\n\n"
            
        except Exception as e:
            stack_trace = traceback.format_exc()
            logger.exception(f"[AI Stream] Error in generate(): {str(e)}")
            yield f"data: {json.dumps({'type': 'error', 'message': str(e), 'error_type': type(e).__name__, 'stack_trace': stack_trace})}\n\n"
    
    logger.info("[AI Stream] Returning SSE response")
    return Response(
        stream_with_context(generate()),
        mimetype='text/event-stream',
        headers={
            'Cache-Control': 'no-cache',
            'X-Accel-Buffering': 'no'
        }
    )

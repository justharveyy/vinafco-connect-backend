"""
seed_all.py
-----------
Seeds Vessels, Routes, and UpcomingAvailability for the Vinafco agentic booking system.
Run with: python seed_all.py
"""

from app import app
from app.models import db, Vessels, Routes, UpcomingAvailability
from datetime import datetime, timedelta

# ════════════════════════════════════════════════════════════════════════
#  CONFIG
# ════════════════════════════════════════════════════════════════════════

HPH_SGN_DISTANCE = 1150.0   # km by sea, Hai Phong → Ho Chi Minh City
BASE_QUOTE       = 7.75     # VND per kg per km

# DWT capacity per vessel (from AIS data)
# Morning Vinafco: DWT 8,721t  |  Vinafco 26: DWT 7,200t
# We use 80% of DWT as bookable weight (reserve 20% for vessel ops/ballast)
MORNING_VINAFCO_CAPACITY = 8721 * 1000 * 0.80   # kg
VINAFCO_26_CAPACITY      = 7200 * 1000 * 0.80   # kg

NOW = datetime.now()

# ════════════════════════════════════════════════════════════════════════
#  VESSELS
# ════════════════════════════════════════════════════════════════════════

VESSELS = [
    {
        "vessel_code":          "VFC-MV",
        "vessel_name":          "Morning Vinafco",
        "latest_status":        "Active",
        "speed":                8.2,
        "course":               0.0,
        "true_heading":         0.0,
        "draught":              8.2,
        "reported_destination": "Hai Phong",
        "reported_eta":         NOW + timedelta(days=2),
        "matched_destination":  "Hai Phong Port",
        "vessel_type":          "Container Ship",
        "last_updated":         NOW,
        "flag":                 "Vietnam",
        "photo":                "",
        "call_sign":            "XVHH",
        "transponder_class":    "A",
        "mmsi_number":          "574134000",
    },
    {
        "vessel_code":          "VFC-26",
        "vessel_name":          "Vinafco 26",
        "latest_status":        "Active",
        "speed":                8.3,
        "course":               72.3,
        "true_heading":         71.0,
        "draught":              6.8,
        "reported_destination": "Ho Chi Minh City",
        "reported_eta":         NOW + timedelta(days=1),
        "matched_destination":  "Ho Chi Minh City Port",
        "vessel_type":          "Container Ship",
        "last_updated":         NOW,
        "flag":                 "Vietnam",
        "photo":                "",
        "call_sign":            "3WMC9",
        "transponder_class":    "A",
        "mmsi_number":          "574002190",
    },
]

# ════════════════════════════════════════════════════════════════════════
#  ROUTES
# Both vessels run the same HPH ↔ SGN corridor, both directions
# ════════════════════════════════════════════════════════════════════════

ROUTES = [
    # Morning Vinafco
    {
        "vessel_id":      "VFC-MV",
        "quote_name":     "HPH-SGN Standard",
        "from_port":      "Hai Phong",
        "from_port_code": "HPH",
        "to_port":        "Ho Chi Minh City",
        "to_port_code":   "SGN",
        "quote":          BASE_QUOTE,
        "total_distance": HPH_SGN_DISTANCE,
    },
    {
        "vessel_id":      "VFC-MV",
        "quote_name":     "SGN-HPH Standard",
        "from_port":      "Ho Chi Minh City",
        "from_port_code": "SGN",
        "to_port":        "Hai Phong",
        "to_port_code":   "HPH",
        "quote":          BASE_QUOTE,
        "total_distance": HPH_SGN_DISTANCE,
    },
    # Vinafco 26
    {
        "vessel_id":      "VFC-26",
        "quote_name":     "HPH-SGN Standard",
        "from_port":      "Hai Phong",
        "from_port_code": "HPH",
        "to_port":        "Ho Chi Minh City",
        "to_port_code":   "SGN",
        "quote":          BASE_QUOTE,
        "total_distance": HPH_SGN_DISTANCE,
    },
    {
        "vessel_id":      "VFC-26",
        "quote_name":     "SGN-HPH Standard",
        "from_port":      "Ho Chi Minh City",
        "from_port_code": "SGN",
        "to_port":        "Hai Phong",
        "to_port_code":   "HPH",
        "quote":          BASE_QUOTE,
        "total_distance": HPH_SGN_DISTANCE,
    },
]

# ════════════════════════════════════════════════════════════════════════
#  UPCOMING AVAILABILITY
#
#  Each vessel does a round trip roughly every 6 days:
#    ~140h sailing (1150km / 8.2kn) + ~4h port ops each end ≈ 6 days
#
#  We seed 4 upcoming sailings per vessel per direction (8 weeks coverage).
#  Transit time calculated from speed:
#    Morning Vinafco: 1150 / 8.2  = ~140h
#    Vinafco 26:      1150 / 8.3  = ~138.5h
#
#  departure_date_time and arrival_date_time stored as Unix timestamp (Float)
#  because the model uses db.Float for those columns.
# ════════════════════════════════════════════════════════════════════════

def ts(dt: datetime) -> float:
    return dt.timestamp()

MV_TRANSIT  = timedelta(hours=round(HPH_SGN_DISTANCE / 8.2, 1))
V26_TRANSIT = timedelta(hours=round(HPH_SGN_DISTANCE / 8.3, 1))
CYCLE       = timedelta(days=6)   # full round-trip cycle per vessel

# First departure: 7 days from now (matches booking.estimated_start_time logic)
MV_FIRST_DEP  = NOW + timedelta(days=7)
V26_FIRST_DEP = NOW + timedelta(days=7, hours=12)   # offset so they're not identical

AVAILABILITY = []

for i in range(4):   # 4 sailings each direction each vessel = 8 weeks coverage

    # ── Morning Vinafco ──────────────────────────────────────────────
    mv_hph_dep = MV_FIRST_DEP  + CYCLE * i
    mv_hph_arr = mv_hph_dep    + MV_TRANSIT
    AVAILABILITY.append({
        "vessel_id":            "VFC-MV",
        "available_weight":     MORNING_VINAFCO_CAPACITY,
        "remaining_weight":     MORNING_VINAFCO_CAPACITY,
        "departure_date_time":  ts(mv_hph_dep),
        "arrival_date_time":    ts(mv_hph_arr),
        "depart_from":          "Hai Phong",
        "depart_from_port_code":"HPH",
        "arrive_to":            "Ho Chi Minh City",
        "arrive_to_port_code":  "SGN",
        "last_updated":         NOW,
    })

    # Return leg (SGN → HPH): departs ~8h after arrival at SGN (port ops)
    mv_sgn_dep = mv_hph_arr   + timedelta(hours=8)
    mv_sgn_arr = mv_sgn_dep   + MV_TRANSIT
    AVAILABILITY.append({
        "vessel_id":            "VFC-MV",
        "available_weight":     MORNING_VINAFCO_CAPACITY,
        "remaining_weight":     MORNING_VINAFCO_CAPACITY,
        "departure_date_time":  ts(mv_sgn_dep),
        "arrival_date_time":    ts(mv_sgn_arr),
        "depart_from":          "Ho Chi Minh City",
        "depart_from_port_code":"SGN",
        "arrive_to":            "Hai Phong",
        "arrive_to_port_code":  "HPH",
        "last_updated":         NOW,
    })

    # ── Vinafco 26 ───────────────────────────────────────────────────
    v26_hph_dep = V26_FIRST_DEP + CYCLE * i
    v26_hph_arr = v26_hph_dep   + V26_TRANSIT
    AVAILABILITY.append({
        "vessel_id":            "VFC-26",
        "available_weight":     VINAFCO_26_CAPACITY,
        "remaining_weight":     VINAFCO_26_CAPACITY,
        "departure_date_time":  ts(v26_hph_dep),
        "arrival_date_time":    ts(v26_hph_arr),
        "depart_from":          "Hai Phong",
        "depart_from_port_code":"HPH",
        "arrive_to":            "Ho Chi Minh City",
        "arrive_to_port_code":  "SGN",
        "last_updated":         NOW,
    })

    v26_sgn_dep = v26_hph_arr   + timedelta(hours=8)
    v26_sgn_arr = v26_sgn_dep   + V26_TRANSIT
    AVAILABILITY.append({
        "vessel_id":            "VFC-26",
        "available_weight":     VINAFCO_26_CAPACITY,
        "remaining_weight":     VINAFCO_26_CAPACITY,
        "departure_date_time":  ts(v26_sgn_dep),
        "arrival_date_time":    ts(v26_sgn_arr),
        "depart_from":          "Ho Chi Minh City",
        "depart_from_port_code":"SGN",
        "arrive_to":            "Hai Phong",
        "arrive_to_port_code":  "HPH",
        "last_updated":         NOW,
    })


# ════════════════════════════════════════════════════════════════════════
#  SEED FUNCTION
# ════════════════════════════════════════════════════════════════════════

def seed():
    with app.app_context():

        # ── Vessels ──────────────────────────────────────────────────
        print("\n── Vessels ──")
        for v in VESSELS:
            if Vessels.query.filter_by(vessel_code=v["vessel_code"]).first():
                print(f"  SKIP  {v['vessel_name']} (already exists)")
                continue
            db.session.add(Vessels(**v))
            print(f"  ADD   {v['vessel_name']}")

        # ── Routes ───────────────────────────────────────────────────
        print("\n── Routes ──")
        for r in ROUTES:
            if Routes.query.filter_by(
                vessel_id=r["vessel_id"],
                from_port=r["from_port"],
                to_port=r["to_port"]
            ).first():
                print(f"  SKIP  {r['vessel_id']} {r['from_port_code']}→{r['to_port_code']} (already exists)")
                continue
            db.session.add(Routes(**r))
            print(f"  ADD   {r['vessel_id']} {r['from_port_code']}→{r['to_port_code']}")

        # ── Upcoming Availability ─────────────────────────────────────
        print("\n── Upcoming Availability ──")
        # Clear existing future slots before re-seeding so re-runs are idempotent
        deleted = UpcomingAvailability.query.filter(
            UpcomingAvailability.departure_date_time >= ts(NOW)
        ).delete()
        if deleted:
            print(f"  CLEARED {deleted} existing future slots")

        for a in AVAILABILITY:
            db.session.add(UpcomingAvailability(**a))

        print(f"  ADD   {len(AVAILABILITY)} availability slots")
        print(f"        ({len(AVAILABILITY) // 4} sailings × 2 directions × 2 vessels)")

        db.session.commit()
        print("\n✓ Seed complete.\n")

        # ── Summary ──────────────────────────────────────────────────
        print("Slots seeded:")
        slots = UpcomingAvailability.query.order_by(
            UpcomingAvailability.departure_date_time
        ).all()
        for s in slots:
            dep = datetime.fromtimestamp(s.departure_date_time)
            arr = datetime.fromtimestamp(s.arrival_date_time)
            cap_t = s.available_weight / 1000
            print(
                f"  {s.vessel_id:8}  {s.depart_from_port_code}→{s.arrive_to_port_code}"
                f"  dep {dep.strftime('%Y-%m-%d %H:%M')}"
                f"  arr {arr.strftime('%Y-%m-%d %H:%M')}"
                f"  cap {cap_t:,.0f}t"
            )


if __name__ == "__main__":
    seed()
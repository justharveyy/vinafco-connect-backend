# seed_vinafco.py
from app import app
from app.models import db, Vessels, Routes
from datetime import datetime

# HPH → SGN distance is ~1,150 km by sea
# Quote per kg: simplify to ~7.75 VND/km/kg (mid of 6.5M-8.95M range for ~1150km)
# So base quote per (kg * km) = 7.75 VND → route.quote = 7.75, distance = 1150
# That gives: 1 kg * 1150 km * 7.75 = ~8,912 VND/kg, reasonable mid-market

HPH_SGN_DISTANCE = 1150.0   # nautical-ish km, HPH to SGN
HPH_SGN_QUOTE    = 7.75     # VND per kg per km unit

vessels = [
    {
        "vessel_code":          "VFC-MV",
        "vessel_name":          "Morning Vinafco",
        "latest_status":        "Active",
        "speed":                8.2,    # knots avg (from AIS data)
        "course":               0.0,
        "true_heading":         0.0,
        "draught":              8.2,    # avg draught in metres
        "reported_destination": "Hai Phong",
        "reported_eta":         datetime(2026, 6, 1, 9, 0),
        "matched_destination":  "Hai Phong Port",
        "vessel_type":          "Container Ship",
        "last_updated":         datetime.now(),
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
        "speed":                8.3,    # knots (from AIS, course 72.3°)
        "course":               72.3,
        "true_heading":         71.0,
        "draught":              6.8,
        "reported_destination": "Da Nang",
        "reported_eta":         datetime(2026, 6, 1, 9, 0),
        "matched_destination":  "Da Nang Port",
        "vessel_type":          "Container Ship",
        "last_updated":         datetime.now(),
        "flag":                 "Vietnam",
        "photo":                "",
        "call_sign":            "3WMC9",
        "transponder_class":    "A",
        "mmsi_number":          "574002190",
    },
]

routes = [
    # Morning Vinafco — HPH ↔ SGN
    {
        "vessel_id":       "VFC-MV",
        "quote_name":      "HPH-SGN Standard",
        "from_port":       "Hai Phong",
        "from_port_code":  "HPH",
        "to_port":         "Ho Chi Minh City",
        "to_port_code":    "SGN",
        "quote":           HPH_SGN_QUOTE,
        "total_distance":  HPH_SGN_DISTANCE,
    },
    {
        "vessel_id":       "VFC-MV",
        "quote_name":      "SGN-HPH Standard",
        "from_port":       "Ho Chi Minh City",
        "from_port_code":  "SGN",
        "to_port":         "Hai Phong",
        "to_port_code":    "HPH",
        "quote":           HPH_SGN_QUOTE,
        "total_distance":  HPH_SGN_DISTANCE,
    },
    # Vinafco 26 — HPH ↔ SGN
    {
        "vessel_id":       "VFC-26",
        "quote_name":      "HPH-SGN Standard",
        "from_port":       "Hai Phong",
        "from_port_code":  "HPH",
        "to_port":         "Ho Chi Minh City",
        "to_port_code":    "SGN",
        "quote":           HPH_SGN_QUOTE,
        "total_distance":  HPH_SGN_DISTANCE,
    },
    {
        "vessel_id":       "VFC-26",
        "quote_name":      "SGN-HPH Standard",
        "from_port":       "Ho Chi Minh City",
        "from_port_code":  "SGN",
        "to_port":         "Hai Phong",
        "to_port_code":    "HPH",
        "quote":           HPH_SGN_QUOTE,
        "total_distance":  HPH_SGN_DISTANCE,
    },
]

def seed():
    with app.app_context():
        for v in vessels:
            existing = Vessels.query.filter_by(vessel_code=v["vessel_code"]).first()
            if existing:
                print(f"Skipping {v['vessel_name']} — already exists")
                continue
            db.session.add(Vessels(**v))
            print(f"Inserted vessel: {v['vessel_name']}")

        for r in routes:
            existing = Routes.query.filter_by(
                vessel_id=r["vessel_id"],
                from_port=r["from_port"],
                to_port=r["to_port"]
            ).first()
            if existing:
                print(f"Skipping route {r['from_port_code']}→{r['to_port_code']} for {r['vessel_id']} — already exists")
                continue
            db.session.add(Routes(**r))
            print(f"Inserted route: {r['vessel_id']} {r['from_port_code']}→{r['to_port_code']}")

        db.session.commit()
        print("Done.")

if __name__ == "__main__":
    seed()
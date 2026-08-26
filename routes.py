"""
Airport route data and standard flight profiles.
"""
from dataclasses import dataclass
import json
from pathlib import Path
from typing import Dict, Tuple

# Great circle distance & standard nautical mile matrix
STANDARD_ROUTES = {
    ("HKJK", "KGL"): {"distance_nm": 412, "flight_time_hr": 1.20, "contingency_pct": 0.05, "alt_burn_kg": 900},
    ("HKJK", "EBB"): {"distance_nm": 282, "flight_time_hr": 0.95, "contingency_pct": 0.05, "alt_burn_kg": 850},
    ("HKJK", "HKMO"): {"distance_nm": 230, "flight_time_hr": 0.80, "contingency_pct": 0.05, "alt_burn_kg": 750},
    ("HKJK", "DAR"): {"distance_nm": 360, "flight_time_hr": 1.10, "contingency_pct": 0.05, "alt_burn_kg": 900},
    ("HKJK", "JNB"): {"distance_nm": 1605, "flight_time_hr": 4.10, "contingency_pct": 0.05, "alt_burn_kg": 1800},
    ("HKJK", "DXB"): {"distance_nm": 1918, "flight_time_hr": 4.80, "contingency_pct": 0.05, "alt_burn_kg": 2000},
    ("HKJK", "LHR"): {"distance_nm": 3685, "flight_time_hr": 8.75, "contingency_pct": 0.05, "alt_burn_kg": 3500},
    ("HKJK", "BOM"): {"distance_nm": 2445, "flight_time_hr": 5.80, "contingency_pct": 0.05, "alt_burn_kg": 2200},
}

def load_fuel_prices(filepath: str = None) -> Dict[str, dict]:
    if filepath is None:
        filepath = Path(__file__).parent.parent / "data" / "fuel_prices.json"
    with open(filepath, "r") as f:
        return json.load(f)

def get_sector_profile(origin: str, destination: str) -> dict:
    key = (origin.upper(), destination.upper())
    rev_key = (destination.upper(), origin.upper())
    if key in STANDARD_ROUTES:
        return STANDARD_ROUTES[key]
    elif rev_key in STANDARD_ROUTES:
        return STANDARD_ROUTES[rev_key]
    else:
        # Default fallback estimate
        return {"distance_nm": 500, "flight_time_hr": 1.40, "contingency_pct": 0.05, "alt_burn_kg": 1000}

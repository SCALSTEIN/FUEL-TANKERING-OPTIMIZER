"""
Aircraft specifications and aerodynamic weight & balance constraints.
"""
from dataclasses import dataclass
import json
from pathlib import Path
from typing import Dict

@dataclass
class AircraftPerformance:
    aircraft_type: str
    name: str
    dow_kg: float
    mzfw_kg: float
    mtow_kg: float
    mlw_kg: float
    max_fuel_capacity_kg: float
    base_burn_rate_kg_hr: float
    carry_penalty_alpha: float
    cruise_speed_tas_kts: float

    @classmethod
    def from_dict(cls, ac_type: str, data: dict) -> "AircraftPerformance":
        return cls(
            aircraft_type=ac_type,
            name=data.get("name", ac_type),
            dow_kg=float(data["DOW_kg"]),
            mzfw_kg=float(data["MZFW_kg"]),
            mtow_kg=float(data["MTOW_kg"]),
            mlw_kg=float(data["MLW_kg"]),
            max_fuel_capacity_kg=float(data["max_fuel_capacity_kg"]),
            base_burn_rate_kg_hr=float(data["base_burn_rate_kg_hr"]),
            carry_penalty_alpha=float(data["carry_penalty_alpha"]),
            cruise_speed_tas_kts=float(data.get("cruise_speed_tas_kts", 450.0))
        )

def load_aircraft_registry(filepath: str = None) -> Dict[str, AircraftPerformance]:
    if filepath is None:
        filepath = Path(__file__).parent.parent / "data" / "aircraft_specs.json"
    with open(filepath, "r") as f:
        data = json.load(f)
    return {k: AircraftPerformance.from_dict(k, v) for k, v in data.items()}

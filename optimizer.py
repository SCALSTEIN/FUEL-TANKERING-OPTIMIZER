"""
Core Economic Fuel Tankering and Cost-of-Carry Engine.
"""
from dataclasses import dataclass
import numpy as np
from src.aircraft import AircraftPerformance

# Constants
JET_A1_DENSITY_KG_PER_LITER = 0.804
LITERS_PER_US_GALLON = 3.78541
KG_PER_US_GALLON = JET_A1_DENSITY_KG_PER_LITER * LITERS_PER_US_GALLON # ~3.0434 kg/gal

@dataclass
class TankeringEvaluation:
    origin_icao: str
    dest_icao: str
    aircraft_type: str
    payload_kg: float
    flight_time_hr: float
    origin_fuel_price_per_kg: float
    dest_fuel_price_per_kg: float
    price_delta_per_kg: float
    recommended_tanker_kg: float
    fuel_burn_penalty_kg: float
    gross_savings_usd: float
    net_economic_benefit_usd: float
    takeoff_weight_kg: float
    landing_weight_kg: float
    mtow_limit_kg: float
    mlw_limit_kg: float
    limiting_factor: str
    is_tankering_viable: bool
    cost_of_carry_pct: float

class TankeringOptimizer:
    def __init__(self, aircraft: AircraftPerformance):
        self.aircraft = aircraft

    @staticmethod
    def usd_per_gal_to_usd_per_kg(price_usd_per_gal: float) -> float:
        return price_usd_per_gal / KG_PER_US_GALLON

    def compute_mission_fuel(self, flight_time_hr: float, alt_burn_kg: float = 1000.0, contingency_pct: float = 0.05) -> dict:
        """Calculates standard ICAO reserve & trip fuel without tankering."""
        trip_burn = self.aircraft.base_burn_rate_kg_hr * flight_time_hr
        contingency = trip_burn * contingency_pct
        final_reserve = self.aircraft.base_burn_rate_kg_hr * 0.5  # 30 mins holding
        minimum_required_departure_fuel = trip_burn + contingency + alt_burn_kg + final_reserve
        return {
            "trip_burn_kg": trip_burn,
            "contingency_kg": contingency,
            "alternate_burn_kg": alt_burn_kg,
            "final_reserve_kg": final_reserve,
            "min_required_fuel_kg": minimum_required_departure_fuel
        }

    def evaluate_tankering(
        self,
        origin_icao: str,
        dest_icao: str,
        origin_price_usd_per_gal: float,
        dest_price_usd_per_gal: float,
        payload_kg: float,
        flight_time_hr: float,
        alt_burn_kg: float = 1000.0,
        return_leg_fuel_demand_kg: float = 4000.0
    ) -> TankeringEvaluation:
        origin_p_kg = self.usd_per_gal_to_usd_per_kg(origin_price_usd_per_gal)
        dest_p_kg = self.usd_per_gal_to_usd_per_kg(dest_price_usd_per_gal)
        price_delta = dest_p_kg - origin_p_kg

        mission_fuel = self.compute_mission_fuel(flight_time_hr, alt_burn_kg)
        min_dep_fuel = mission_fuel["min_required_fuel_kg"]
        trip_burn = mission_fuel["trip_burn_kg"]

        # Cost of carry factor alpha per flight hour
        # Incremental fuel burn = tanker_amount * (e^(alpha * T) - 1)
        cost_of_carry_fraction = float(np.expm1(self.aircraft.carry_penalty_alpha * flight_time_hr))

        # Check weight ceilings
        zfw = self.aircraft.dow_kg + payload_kg
        if zfw > self.aircraft.mzfw_kg:
            raise ValueError(f"Zero Fuel Weight ({zfw:.0f} kg) exceeds MZFW ({self.aircraft.mzfw_kg:.0f} kg)!")

        # Allowable extra mass by Takeoff Weight limit
        max_fuel_by_tow = self.aircraft.mtow_kg - zfw
        max_tanker_by_tow = max_fuel_by_tow - min_dep_fuel

        # Allowable extra mass by Landing Weight limit
        # Landing Weight = ZFW + (Departure Fuel - Trip Burn - Delta Burn)
        # delta burn approx tanker * cost_of_carry_fraction
        # MLW >= ZFW + (min_dep_fuel - trip_burn) + tanker
        reserves_at_landing = min_dep_fuel - trip_burn
        max_tanker_by_law = (self.aircraft.mlw_kg - (zfw + reserves_at_landing)) / (1.0 + 0.0)

        # Allowable fuel by tank volume limit
        max_tanker_by_tank = self.aircraft.max_fuel_capacity_kg - min_dep_fuel

        # Overall physical ceiling for tankered fuel
        max_physically_possible = max(0.0, min(max_tanker_by_tow, max_tanker_by_law, max_tanker_by_tank))

        # Identify constraining limit
        limits = {
            "MTOW (Max Takeoff Weight)": max_tanker_by_tow,
            "MLW (Max Landing Weight)": max_tanker_by_law,
            "Fuel Tank Volume Capacity": max_tanker_by_tank,
            "Downline Fuel Demand Cap": return_leg_fuel_demand_kg
        }
        limiting_factor = min(limits, key=limits.get)

        # Optimization decision:
        # Net Benefit per kg tanker = dest_p_kg - origin_p_kg * (1 + cost_of_carry_fraction)
        marginal_benefit_per_kg = dest_p_kg - (origin_p_kg * (1.0 + cost_of_carry_fraction))

        if marginal_benefit_per_kg > 0 and max_physically_possible > 0:
            recommended_tanker = min(max_physically_possible, return_leg_fuel_demand_kg)
            viable = True
        else:
            recommended_tanker = 0.0
            viable = False

        burn_penalty = recommended_tanker * cost_of_carry_fraction
        gross_savings = recommended_tanker * dest_p_kg
        total_uplift_cost = (recommended_tanker + burn_penalty) * origin_p_kg
        net_benefit = gross_savings - total_uplift_cost if viable else 0.0

        actual_tow = zfw + min_dep_fuel + recommended_tanker + burn_penalty
        actual_law = zfw + reserves_at_landing + recommended_tanker

        return TankeringEvaluation(
            origin_icao=origin_icao,
            dest_icao=dest_icao,
            aircraft_type=self.aircraft.aircraft_type,
            payload_kg=payload_kg,
            flight_time_hr=flight_time_hr,
            origin_fuel_price_per_kg=origin_p_kg,
            dest_fuel_price_per_kg=dest_p_kg,
            price_delta_per_kg=price_delta,
            recommended_tanker_kg=recommended_tanker,
            fuel_burn_penalty_kg=burn_penalty,
            gross_savings_usd=gross_savings,
            net_economic_benefit_usd=net_benefit,
            takeoff_weight_kg=actual_tow,
            landing_weight_kg=actual_law,
            mtow_limit_kg=self.aircraft.mtow_kg,
            mlw_limit_kg=self.aircraft.mlw_kg,
            limiting_factor=limiting_factor if viable else "Price differential negative / uneconomic",
            is_tankering_viable=viable,
            cost_of_carry_pct=cost_of_carry_fraction * 100.0
        )

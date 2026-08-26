"""
Commercial Flight Operations: Fuel Burn & Economic Tankering Optimizer
Author: Pascal Mudimba (@scalstein)
"""

import json
import os
import sys
from dataclasses import dataclass
from typing import Dict

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

# ---------------------------------------------------------
# 1. DATA MODELS & BUILT-IN FALLBACK REGISTRIES
# ---------------------------------------------------------

DEFAULT_AIRCRAFT_DATA = {
    "B737-800": {
        "name": "Boeing 737-800",
        "DOW_kg": 41413,
        "MZFW_kg": 62731,
        "MTOW_kg": 79010,
        "MLW_kg": 66360,
        "max_fuel_capacity_kg": 20894,
        "base_burn_rate_kg_hr": 2400.0,
        "carry_penalty_alpha": 0.038,
        "cruise_speed_tas_kts": 450,
    },
    "E190": {
        "name": "Embraer E190-E1",
        "DOW_kg": 28080,
        "MZFW_kg": 40800,
        "MTOW_kg": 51800,
        "MLW_kg": 44000,
        "max_fuel_capacity_kg": 12971,
        "base_burn_rate_kg_hr": 1750.0,
        "carry_penalty_alpha": 0.035,
        "cruise_speed_tas_kts": 440,
    },
    "B787-8": {
        "name": "Boeing 787-8 Dreamliner",
        "DOW_kg": 119950,
        "MZFW_kg": 161025,
        "MTOW_kg": 227930,
        "MLW_kg": 172365,
        "max_fuel_capacity_kg": 101456,
        "base_burn_rate_kg_hr": 4800.0,
        "carry_penalty_alpha": 0.032,
        "cruise_speed_tas_kts": 490,
    },
}

DEFAULT_FUEL_PRICES = {
    "HKJK": {"name": "Nairobi (Jomo Kenyatta)", "price_per_gal_usd": 2.85},
    "HKMO": {"name": "Mombasa (Moi Intl)", "price_per_gal_usd": 2.92},
    "HKEL": {"name": "Eldoret Intl", "price_per_gal_usd": 2.98},
    "EBB": {"name": "Entebbe Intl (Uganda)", "price_per_gal_usd": 3.45},
    "KGL": {"name": "Kigali Intl (Rwanda)", "price_per_gal_usd": 3.65},
    "DAR": {"name": "Dar es Salaam (Julius Nyerere)", "price_per_gal_usd": 3.20},
    "JNB": {"name": "Johannesburg (OR Tambo)", "price_per_gal_usd": 2.72},
    "DXB": {"name": "Dubai Intl (UAE)", "price_per_gal_usd": 2.40},
    "LHR": {"name": "London Heathrow (UK)", "price_per_gal_usd": 2.65},
    "BOM": {"name": "Mumbai (Chhatrapati Shivaji)", "price_per_gal_usd": 2.95},
}

STANDARD_ROUTES = {
    ("HKJK", "KGL"): {"distance_nm": 412, "flight_time_hr": 1.20, "alt_burn_kg": 900},
    ("HKJK", "EBB"): {"distance_nm": 282, "flight_time_hr": 0.95, "alt_burn_kg": 850},
    ("HKJK", "HKMO"): {"distance_nm": 230, "flight_time_hr": 0.80, "alt_burn_kg": 750},
    ("HKJK", "DAR"): {"distance_nm": 360, "flight_time_hr": 1.10, "alt_burn_kg": 900},
    ("HKJK", "JNB"): {"distance_nm": 1605, "flight_time_hr": 4.10, "alt_burn_kg": 1800},
    ("HKJK", "DXB"): {"distance_nm": 1918, "flight_time_hr": 4.80, "alt_burn_kg": 2000},
    ("HKJK", "LHR"): {"distance_nm": 3685, "flight_time_hr": 8.75, "alt_burn_kg": 3500},
    ("HKJK", "BOM"): {"distance_nm": 2445, "flight_time_hr": 5.80, "alt_burn_kg": 2200},
}

JET_A1_DENSITY_KG_PER_LITER = 0.804
LITERS_PER_US_GALLON = 3.78541
KG_PER_US_GALLON = JET_A1_DENSITY_KG_PER_LITER * LITERS_PER_US_GALLON  # ~3.0434 kg/gal


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
        cruise_speed_tas_kts=float(data.get("cruise_speed_tas_kts", 450.0)),
    )


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

  def compute_mission_fuel(
      self,
      flight_time_hr: float,
      alt_burn_kg: float = 1000.0,
      contingency_pct: float = 0.05,
  ) -> dict:
    trip_burn = self.aircraft.base_burn_rate_kg_hr * flight_time_hr
    contingency = trip_burn * contingency_pct
    final_reserve = self.aircraft.base_burn_rate_kg_hr * 0.5  # 30-min holding
    minimum_departure_fuel = (
        trip_burn + contingency + alt_burn_kg + final_reserve
    )
    return {
        "trip_burn_kg": trip_burn,
        "contingency_kg": contingency,
        "alternate_burn_kg": alt_burn_kg,
        "final_reserve_kg": final_reserve,
        "min_required_fuel_kg": minimum_departure_fuel,
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
      return_leg_fuel_demand_kg: float = 4000.0,
  ) -> TankeringEvaluation:
    origin_p_kg = self.usd_per_gal_to_usd_per_kg(origin_price_usd_per_gal)
    dest_p_kg = self.usd_per_gal_to_usd_per_kg(dest_price_usd_per_gal)
    price_delta = dest_p_kg - origin_p_kg

    mission_fuel = self.compute_mission_fuel(flight_time_hr, alt_burn_kg)
    min_dep_fuel = mission_fuel["min_required_fuel_kg"]
    trip_burn = mission_fuel["trip_burn_kg"]

    cost_of_carry_fraction = float(
        np.expm1(self.aircraft.carry_penalty_alpha * flight_time_hr)
    )

    zfw = self.aircraft.dow_kg + payload_kg
    if zfw > self.aircraft.mzfw_kg:
      payload_kg = max(0.0, self.aircraft.mzfw_kg - self.aircraft.dow_kg)
      zfw = self.aircraft.dow_kg + payload_kg

    max_tanker_by_tow = max(0.0, (self.aircraft.mtow_kg - zfw) - min_dep_fuel)
    reserves_at_landing = min_dep_fuel - trip_burn
    max_tanker_by_law = max(
        0.0, self.aircraft.mlw_kg - (zfw + reserves_at_landing)
    )
    max_tanker_by_tank = max(
        0.0, self.aircraft.max_fuel_capacity_kg - min_dep_fuel
    )

    max_possible = min(
        max_tanker_by_tow, max_tanker_by_law, max_tanker_by_tank
    )

    limits = {
        "MTOW (Max Takeoff Weight)": max_tanker_by_tow,
        "MLW (Max Landing Weight)": max_tanker_by_law,
        "Fuel Tank Capacity": max_tanker_by_tank,
        "Downline Demand Cap": return_leg_fuel_demand_kg,
    }
    limiting_factor = min(limits, key=limits.get)

    marginal_benefit_per_kg = dest_p_kg - (
        origin_p_kg * (1.0 + cost_of_carry_fraction)
    )

    if marginal_benefit_per_kg > 0 and max_possible > 0:
      recommended_tanker = min(max_possible, return_leg_fuel_demand_kg)
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
        limiting_factor=(
            limiting_factor if viable else "Price differential uneconomic"
        ),
        is_tankering_viable=viable,
        cost_of_carry_pct=cost_of_carry_fraction * 100.0,
    )


# ---------------------------------------------------------
# 2. DATA LOADERS (WITH DISK FALLBACK)
# ---------------------------------------------------------


def get_aircraft_registry() -> Dict[str, AircraftPerformance]:
  path = os.path.join(
      os.path.dirname(__file__), "data", "aircraft_specs.json"
  )
  if os.path.exists(path):
    try:
      with open(path, "r") as f:
        data = json.load(f)
      return {k: AircraftPerformance.from_dict(k, v) for k, v in data.items()}
    except Exception:
      pass
  return {
      k: AircraftPerformance.from_dict(k, v)
      for k, v in DEFAULT_AIRCRAFT_DATA.items()
  }


def get_fuel_prices() -> Dict[str, dict]:
  path = os.path.join(os.path.dirname(__file__), "data", "fuel_prices.json")
  if os.path.exists(path):
    try:
      with open(path, "r") as f:
        return json.load(f)
    except Exception:
      pass
  return DEFAULT_FUEL_PRICES


def get_sector(origin: str, dest: str) -> dict:
  k1, k2 = (origin.upper(), dest.upper()), (dest.upper(), origin.upper())
  if k1 in STANDARD_ROUTES:
    return STANDARD_ROUTES[k1]
  if k2 in STANDARD_ROUTES:
    return STANDARD_ROUTES[k2]
  return {
      "distance_nm": 500,
      "flight_time_hr": 1.40,
      "alt_burn_kg": 1000,
  }


# ---------------------------------------------------------
# 3. STREAMLIT USER INTERFACE
# ---------------------------------------------------------

st.set_page_config(
    page_title="Fuel Tankering Optimizer | Flight Ops Engineering",
    layout="wide",
    page_icon="✈️",
)

st.title("✈️ Fuel Burn & Economic Tankering Optimizer")
st.caption(
    "Flight Operations Engineering Decision Support Tool | Direct Operating"
    " Cost (DOC) Optimization"
)

aircraft_dict = get_aircraft_registry()
fuel_prices_dict = get_fuel_prices()

# Sidebar
st.sidebar.header("Operational Flight Parameters")
selected_ac = st.sidebar.selectbox(
    "Aircraft Fleet Type", list(aircraft_dict.keys()), index=0
)
aircraft = aircraft_dict[selected_ac]

stations = list(fuel_prices_dict.keys())
origin_station = st.sidebar.selectbox("Origin Station (Hub)", stations, index=0)
dest_station = st.sidebar.selectbox(
    "Destination Station (Outstation)", stations, index=4
)

sector_info = get_sector(origin_station, dest_station)

st.sidebar.subheader("Flight Sector & Payload Inputs")
flight_time = st.sidebar.slider(
    "Sector Flight Time (Hours)",
    0.5,
    12.0,
    float(sector_info["flight_time_hr"]),
    step=0.05,
)
max_allowable_payload = int(aircraft.mzfw_kg - aircraft.dow_kg)
payload = st.sidebar.slider(
    "Flight Payload (kg)",
    2000,
    max_allowable_payload,
    int(max_allowable_payload * 0.75),
    step=250,
)
downline_demand = st.sidebar.slider(
    "Downline Return Fuel Demand (kg)", 1000, 15000, 4500, step=250
)

st.sidebar.subheader("Fuel Station Pricing ($/US Gallon)")
p_orig_default = fuel_prices_dict[origin_station]["price_per_gal_usd"]
p_dest_default = fuel_prices_dict[dest_station]["price_per_gal_usd"]

p_orig = st.sidebar.number_input(
    f"Origin Price ({origin_station}) [$/gal]",
    value=float(p_orig_default),
    step=0.05,
)
p_dest = st.sidebar.number_input(
    f"Destination Price ({dest_station}) [$/gal]",
    value=float(p_dest_default),
    step=0.05,
)

# Optimize
optimizer = TankeringOptimizer(aircraft)
eval_res = optimizer.evaluate_tankering(
    origin_icao=origin_station,
    dest_icao=dest_station,
    origin_price_usd_per_gal=p_orig,
    dest_price_usd_per_gal=p_dest,
    payload_kg=payload,
    flight_time_hr=flight_time,
    alt_burn_kg=sector_info.get("alt_burn_kg", 1000.0),
    return_leg_fuel_demand_kg=downline_demand,
)

# KPI Metrics
col1, col2, col3, col4 = st.columns(4)
with col1:
  st.metric(
      "Optimal Tanker Uplift",
      f"{eval_res.recommended_tanker_kg:,.0f} kg",
      delta="VIABLE" if eval_res.is_tankering_viable else "NO TANKER",
  )
with col2:
  st.metric(
      "Net Economic Benefit",
      f"${eval_res.net_economic_benefit_usd:,.2f}",
      delta=(
          f"+${eval_res.net_economic_benefit_usd:,.2f}"
          if eval_res.is_tankering_viable
          else "$0.00"
      ),
  )
with col3:
  st.metric(
      "Cost of Carry Penalty",
      f"{eval_res.fuel_burn_penalty_kg:,.0f} kg",
      f"{eval_res.cost_of_carry_pct:.2f}% / sector",
  )
with col4:
  st.metric("Limiting Factor", eval_res.limiting_factor)

st.divider()

# Tabs
tab1, tab2, tab3 = st.tabs([
    "📊 Performance & Weight Envelope",
    "📈 Price Sensitivity Analysis",
    "📑 Dispatch & Operational Summary",
])

with tab1:
  c_left, c_right = st.columns(2)
  with c_left:
    st.subheader("Structural Weight Margins")
    df_weights = pd.DataFrame({
        "Metric": [
            "TOW (Takeoff Weight)",
            "LAW (Landing Weight)",
            "ZFW (Zero Fuel Weight)",
        ],
        "Actual (kg)": [
            eval_res.takeoff_weight_kg,
            eval_res.landing_weight_kg,
            aircraft.dow_kg + payload,
        ],
        "Structural Limit (kg)": [
            eval_res.mtow_limit_kg,
            eval_res.mlw_limit_kg,
            aircraft.mzfw_kg,
        ],
        "Margin Remaining (kg)": [
            eval_res.mtow_limit_kg - eval_res.takeoff_weight_kg,
            eval_res.mlw_limit_kg - eval_res.landing_weight_kg,
            aircraft.mzfw_kg - (aircraft.dow_kg + payload),
        ],
    })
    st.dataframe(
        df_weights.style.format({
            "Actual (kg)": "{:,.0f}",
            "Structural Limit (kg)": "{:,.0f}",
            "Margin Remaining (kg)": "{:,.0f}",
        }),
        use_container_width=True,
    )

    fig_weight = go.Figure(
        data=[
            go.Bar(
                name="Actual Flight Weight",
                x=["TOW", "LAW", "ZFW"],
                y=[
                    eval_res.takeoff_weight_kg,
                    eval_res.landing_weight_kg,
                    aircraft.dow_kg + payload,
                ],
                marker_color="#1E3A8A",
            ),
            go.Bar(
                name="Structural Max Limit",
                x=["TOW", "LAW", "ZFW"],
                y=[
                    eval_res.mtow_limit_kg,
                    eval_res.mlw_limit_kg,
                    aircraft.mzfw_kg,
                ],
                marker_color="#94A3B8",
            ),
        ]
    )
    fig_weight.update_layout(
        barmode="group",
        title="Weight vs Certified Limits",
        yaxis_title="Kilograms (kg)",
        height=320,
    )
    st.plotly_chart(fig_weight, use_container_width=True)

  with c_right:
    st.subheader("Departure Fuel Composition")
    mission = optimizer.compute_mission_fuel(flight_time)
    fuel_breakdown = {
        "Trip Burn": mission["trip_burn_kg"],
        "Contingency (5%)": mission["contingency_kg"],
        "Alternate Fuel": mission["alternate_burn_kg"],
        "Final Holding Reserve": mission["final_reserve_kg"],
        "Tankered Fuel": eval_res.recommended_tanker_kg,
        "Carry Burn Penalty": eval_res.fuel_burn_penalty_kg,
    }
    fig_fuel = px.pie(
        values=list(fuel_breakdown.values()),
        names=list(fuel_breakdown.keys()),
        title="Departure Fuel Breakdown (kg)",
        hole=0.4,
        color_discrete_sequence=px.colors.sequential.Blues_r,
    )
    st.plotly_chart(fig_fuel, use_container_width=True)

with tab2:
  st.subheader("Price Differential vs Net Savings Curve")
  delta_prices = np.linspace(-1.0, 2.5, 30)
  savings_curve = []
  for d_p in delta_prices:
    temp_dest_p = p_orig + d_p
    res = optimizer.evaluate_tankering(
        origin_icao=origin_station,
        dest_icao=dest_station,
        origin_price_usd_per_gal=p_orig,
        dest_price_usd_per_gal=temp_dest_p,
        payload_kg=payload,
        flight_time_hr=flight_time,
        alt_burn_kg=sector_info.get("alt_burn_kg", 1000.0),
        return_leg_fuel_demand_kg=downline_demand,
    )
    savings_curve.append({
        "Price Delta ($/gal)": d_p,
        "Net Benefit ($)": res.net_economic_benefit_usd,
        "Tankered Fuel (kg)": res.recommended_tanker_kg,
    })
  df_curve = pd.DataFrame(savings_curve)

  fig_curve = px.line(
      df_curve,
      x="Price Delta ($/gal)",
      y="Net Benefit ($)",
      title="Net Benefit vs Outstation Price Spread",
      markers=True,
  )
  fig_curve.add_vline(
      x=p_dest - p_orig,
      line_dash="dash",
      line_color="red",
      annotation_text="Active Differential",
  )
  st.plotly_chart(fig_curve, use_container_width=True)

with tab3:
  st.subheader("Operational Dispatch Recommendation")
  if eval_res.is_tankering_viable:
    st.success(f"""
        **TANKERING RECOMMENDED: SECTOR {origin_station} ➔ {dest_station}**
        * **Recommended Fuel Tanker Uplift:** `{eval_res.recommended_tanker_kg:,.0f} kg`
        * **Projected Direct Cost Saving:** `${eval_res.net_economic_benefit_usd:,.2f}`
        * **Carry Burn Penalty:** `{eval_res.fuel_burn_penalty_kg:,.0f} kg` ({eval_res.cost_of_carry_pct:.2f}% extra burn)
        * **MTOW Buffer Remaining:** `{eval_res.mtow_limit_kg - eval_res.takeoff_weight_kg:,.0f} kg`
        * **MLW Buffer Remaining:** `{eval_res.mlw_limit_kg - eval_res.landing_weight_kg:,.0f} kg`
        """)
  else:
    st.warning(f"""
        **NO TANKERING RECOMMENDED**
        * Fuel price differential between {origin_station} and {dest_station} does not overcome aerodynamic carry burn penalty ({eval_res.cost_of_carry_pct:.2f}%).
        * Carrying extra fuel on this sector results in negative operating margin.
        """)

"""
Streamlit Web Dashboard for Fuel Burn & Economic Tankering Optimizer.
"""
import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from src.aircraft import load_aircraft_registry
from src.routes import load_fuel_prices, get_sector_profile
from src.optimizer import TankeringOptimizer

st.set_page_config(page_title="Fuel Tankering Optimizer | Flight Ops", layout="wide", page_icon="✈️")

st.markdown("""
<style>
    .metric-card {
        background-color: #f8f9fa;
        border-radius: 8px;
        padding: 16px;
        border-left: 4px solid #1E3A8A;
    }
</style>
""", unsafe_allow_html=True)

st.title("✈️ Fuel Burn & Economic Tankering Optimizer")
st.caption("Flight Operations Engineering Decision Support Tool | Direct Operating Cost (DOC) Optimization")

# Load registry & data
aircraft_dict = load_aircraft_registry()
fuel_prices_dict = load_fuel_prices()

# Sidebar Controls
st.sidebar.header("Operational Flight Parameters")

selected_ac = st.sidebar.selectbox("Aircraft Type", list(aircraft_dict.keys()), index=0)
aircraft = aircraft_dict[selected_ac]

stations = list(fuel_prices_dict.keys())
origin_station = st.sidebar.selectbox("Origin Station (Hub)", stations, index=0)
dest_station = st.sidebar.selectbox("Destination Station (Outstation)", stations, index=4)

sector_info = get_sector_profile(origin_station, dest_station)

st.sidebar.subheader("Sector & Payload Inputs")
flight_time = st.sidebar.slider("Sector Flight Time (Hours)", 0.5, 12.0, float(sector_info["flight_time_hr"]), step=0.05)
payload = st.sidebar.slider("Flight Payload (kg)", 2000, int(aircraft.mzfw_kg - aircraft.dow_kg), int((aircraft.mzfw_kg - aircraft.dow_kg)*0.75), step=250)
downline_demand = st.sidebar.slider("Downline Return/Next Leg Fuel Need (kg)", 1000, 15000, 4500, step=250)

st.sidebar.subheader("Fuel Station Pricing ($/US Gallon)")
origin_price_default = fuel_prices_dict[origin_station]["price_per_gal_usd"]
dest_price_default = fuel_prices_dict[dest_station]["price_per_gal_usd"]

p_orig = st.sidebar.number_input(f"Origin Price ({origin_station}) [$/gal]", value=origin_price_default, step=0.05)
p_dest = st.sidebar.number_input(f"Destination Price ({dest_station}) [$/gal]", value=dest_price_default, step=0.05)

# Run Optimization
optimizer = TankeringOptimizer(aircraft)
eval_res = optimizer.evaluate_tankering(
    origin_icao=origin_station,
    dest_icao=dest_station,
    origin_price_usd_per_gal=p_orig,
    dest_price_usd_per_gal=p_dest,
    payload_kg=payload,
    flight_time_hr=flight_time,
    alt_burn_kg=sector_info.get("alt_burn_kg", 1000.0),
    return_leg_fuel_demand_kg=downline_demand
)

# Top KPI Summary Cards
col1, col2, col3, col4 = st.columns(4)
with col1:
    st.metric("Optimal Tanker Uplift", f"{eval_res.recommended_tanker_kg:,.0f} kg", delta=f"{'VIABLE' if eval_res.is_tankering_viable else 'NO TANKER'}")
with col2:
    st.metric("Net Economic Benefit", f"${eval_res.net_economic_benefit_usd:,.2f}", delta=f"+${eval_res.net_economic_benefit_usd:,.2f}" if eval_res.is_tankering_viable else "$0.00")
with col3:
    st.metric("Cost of Carry Penalty", f"{eval_res.fuel_burn_penalty_kg:,.0f} kg", f"{eval_res.cost_of_carry_pct:.2f}% / sector")
with col4:
    st.metric("Limiting Factor", eval_res.limiting_factor)

st.divider()

tab1, tab2, tab3 = st.tabs(["📊 Performance & Weight Envelope", "📈 Price Sensitivity Analysis", "📑 Dispatch & Operational Summary"])

with tab1:
    c_left, c_right = st.columns(2)
    with c_left:
        st.subheader("Weight Limits & Margins")
        df_weights = pd.DataFrame({
            "Metric": ["TOW (Takeoff Weight)", "LAW (Landing Weight)", "ZFW (Zero Fuel Weight)"],
            "Actual (kg)": [eval_res.takeoff_weight_kg, eval_res.landing_weight_kg, aircraft.dow_kg + payload],
            "Structural Limit (kg)": [eval_res.mtow_limit_kg, eval_res.mlw_limit_kg, aircraft.mzfw_kg],
            "Margin Remaining (kg)": [
                eval_res.mtow_limit_kg - eval_res.takeoff_weight_kg,
                eval_res.mlw_limit_kg - eval_res.landing_weight_kg,
                aircraft.mzfw_kg - (aircraft.dow_kg + payload)
            ]
        })
        st.dataframe(df_weights.style.format({"Actual (kg)": "{:,.0f}", "Structural Limit (kg)": "{:,.0f}", "Margin Remaining (kg)": "{:,.0f}"}), use_container_width=True)
        
        # Weight Margin Chart
        fig_weight = go.Figure(data=[
            go.Bar(name='Actual Flight Weight', x=['TOW', 'LAW', 'ZFW'], y=[eval_res.takeoff_weight_kg, eval_res.landing_weight_kg, aircraft.dow_kg + payload], marker_color='#2563EB'),
            go.Bar(name='Structural Max Limit', x=['TOW', 'LAW', 'ZFW'], y=[eval_res.mtow_limit_kg, eval_res.mlw_limit_kg, aircraft.mzfw_kg], marker_color='#94A3B8')
        ])
        fig_weight.update_layout(barmode='group', title="Weight vs Structural Limits", yaxis_title="Kilograms (kg)", height=320)
        st.plotly_chart(fig_weight, use_container_width=True)

    with c_right:
        st.subheader("Fuel Breakdown (Uplift Profile)")
        mission = optimizer.compute_mission_fuel(flight_time)
        fuel_breakdown = {
            "Trip Burn": mission["trip_burn_kg"],
            "Contingency": mission["contingency_kg"],
            "Alternate": mission["alternate_burn_kg"],
            "Final Holding Reserve": mission["final_reserve_kg"],
            "Tankered Fuel": eval_res.recommended_tanker_kg,
            "Cost-of-Carry Burn": eval_res.fuel_burn_penalty_kg
        }
        fig_fuel = px.pie(
            values=list(fuel_breakdown.values()),
            names=list(fuel_breakdown.keys()),
            title="Departure Total Fuel Composition",
            hole=0.4,
            color_discrete_sequence=px.colors.sequential.Blues_r
        )
        st.plotly_chart(fig_fuel, use_container_width=True)

with tab2:
    st.subheader("Fuel Price Differential vs Net Savings Curve")
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
            return_leg_fuel_demand_kg=downline_demand
        )
        savings_curve.append({
            "Price Delta ($/gal)": d_p,
            "Net Benefit ($)": res.net_economic_benefit_usd,
            "Tankered Fuel (kg)": res.recommended_tanker_kg
        })
    df_curve = pd.DataFrame(savings_curve)
    
    fig_curve = px.line(df_curve, x="Price Delta ($/gal)", y="Net Benefit ($)", title="Sensitivity: Net Benefit vs Outstation Price Differential", markers=True)
    fig_curve.add_vline(x=p_dest - p_orig, line_dash="dash", line_color="red", annotation_text="Current Differential")
    st.plotly_chart(fig_curve, use_container_width=True)

with tab3:
    st.subheader("Operational Dispatch Recommendation")
    if eval_res.is_tankering_viable:
        st.success(f"""
        **TANKERING RECOMMENDED FOR FLIGHT SECTOR {origin_station} ➔ {dest_station}**
        * **Recommended Fuel Tanker Uplift:** `{eval_res.recommended_tanker_kg:,.0f} kg`
        * **Projected Direct Cost Saving:** `${eval_res.net_economic_benefit_usd:,.2f}`
        * **Carry Burn Overconsumption:** `{eval_res.fuel_burn_penalty_kg:,.0f} kg` ({eval_res.cost_of_carry_pct:.2f}% extra burn)
        * **Dispatch Margin on MTOW:** `{eval_res.mtow_limit_kg - eval_res.takeoff_weight_kg:,.0f} kg` buffer remaining.
        * **Dispatch Margin on MLW:** `{eval_res.mlw_limit_kg - eval_res.landing_weight_kg:,.0f} kg` buffer remaining.
        """)
    else:
        st.warning(f"""
        **NO TANKERING RECOMMENDED**
        * The price differential between {origin_station} and {dest_station} does not offset the aerodynamic cost-of-carry penalty ({eval_res.cost_of_carry_pct:.2f}%).
        * Carrying extra fuel would result in negative direct operating margins.
        """)

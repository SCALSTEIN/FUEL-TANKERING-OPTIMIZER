Markdown# ✈️ Commercial Flight Operations: Fuel Burn & Economic Tankering Optimizer

An end-to-end Flight Operations Engineering decision-support platform designed to model aerodynamic **cost-of-carry** penalties and evaluate **economic fuel tankering** opportunities across regional and long-haul commercial airline sectors (benchmarked on the JKIA hub network).

[![Live Demo](https://static.streamlit.io/badges/streamlit_badge_black_white.svg)](https://scalstein-fuel-tankering-optimizer.streamlit.app/)
[![Python 3.10+](https://img.shields.io/badge/Python-3.10%2B-blue.svg)](https://www.python.org/)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

---

## 📌 1. Operational Context & Problem Statement
Fuel accounts for **25% to 40%** of commercial airline Direct Operating Costs (DOC)[cite: 2]. When operating between hub stations (e.g., Nairobi - HKJK) and regional outstations (e.g., Kigali - KGL, Entebbe - EBB, Dubai - DXB), fuel price differentials can exceed 20–35% due to local supply chains, refinery margins, and taxes[cite: 2].

Carrying extra fuel (*tankering*) from a lower-cost origin to avoid expensive downline fueling saves money on fuel purchase price, but introduces an **aerodynamic cost-of-carry penalty**: the added mass increases required lift, induced drag, and cruise fuel burn[cite: 2].

This system evaluates this non-linear trade-off in real-time, enforcing all structural and regulatory constraints:
1. **Maximum Takeoff Weight (MTOW)**[cite: 2]
2. **Maximum Landing Weight (MLW)**[cite: 2]
3. **Maximum Zero Fuel Weight (MZFW)**[cite: 2]
4. **Usable Fuel Tank Capacity**[cite: 2]
5. **ICAO Annex 6 Fuel Reserve Policy** (Trip + 5% Contingency + Alternate Burn + 30-min Final Holding Reserve)[cite: 2, 6]

---

## 🧮 2. Mathematical Formulation & Engineering Logic

### Non-Linear Cost-of-Carry Penalty
The incremental fuel burn required to transport additional tankered mass $M_{\text{tanker}}$ over a sector of duration $T$ (hours) is modeled using the aircraft-specific aerodynamic penalty factor $\alpha$[cite: 2]:

$$\Delta M_{\text{burn}} = M_{\text{tanker}} \cdot \left( e^{\alpha \cdot T} - 1 \right)$$

* Aircraft aerodynamic carry polars configured in the registry:
  * **Boeing 737-800:** $\alpha = 0.038\text{ hr}^{-1}$[cite: 11]
  * **Embraer E190:** $\alpha = 0.035\text{ hr}^{-1}$[cite: 11]
  * **Boeing 787-8:** $\alpha = 0.032\text{ hr}^{-1}$[cite: 11]

### Net Economic Differential ($\Delta C$)
$$\Delta C = \left( M_{\text{tanker}} \cdot P_{\text{dest}} \right) - \left( (M_{\text{tanker}} + \Delta M_{\text{burn}}) \cdot P_{\text{origin}} \right)$$

*Where:*
* $P_{\text{origin}}, P_{\text{dest}}$: Price per unit mass ($\text{USD/kg}$)[cite: 2].
* **Decision Rule:** Tanker if and only if $\Delta C > 0$, subject to $\min(\text{MTOW Margin}, \text{MLW Margin}, \text{Tank Volume Capacity})$[cite: 2].

---

## 🏗️ 3. Repository Architecture

```text
fuel-tankering-optimizer/
├── data/
│   ├── aircraft_specs.json       # Structural weights (DOW, MZFW, MTOW, MLW) & fuel polars
│   └── fuel_prices.json          # Benchmark regional station fuel prices ($/USG)
├── src/
│   ├── __init__.py
│   ├── aircraft.py               # Aircraft data class models & registry loader
│   ├── optimizer.py              # Cost-of-carry engine & structural constraint solver
│   └── routes.py                 # Sector distance, standard flight times & burn profiles
├── tests/
│   └── test_optimizer.py         # Automated pytest test vectors for edge cases
├── app.py                        # Interactive Streamlit dispatch & sensitivity UI
├── requirements.txt
├── .gitignore
└── README.md
🚀 4. Quickstart & InstallationBash# Clone the repository
git clone [https://github.com/scalstein/fuel-tankering-optimizer.git](https://github.com/scalstein/fuel-tankering-optimizer.git)
cd fuel-tankering-optimizer

# Create and activate virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Run test suite
pytest tests/

# Launch the Streamlit dashboard
streamlit run app.py
📊 5. Dashboard Features & VisualizationsDispatch KPI Summary: Instant identification of whether tankering is viable,
recommended mass uplift, net dollar savings, and carry penalty percentage.
Structural Weight Envelopes: Real-time TOW, LAW, and ZFW validation
with margin buffers against certified airframe ceilings.
Fuel Composition Breakdown: Clear breakdown of Trip, Contingency, Alternate, Final Holding Reserve, and Tankered fuel.
Price Differential Sensitivity Curve: Interactive Plotly graph analyzing break-even economics as outstation fuel prices fluctuate.

👨‍💻 Engineering AuthorPascal Ambogo MudimbaFlight Operations Engineering & Aviation Data SystemsGitHub: @scalsteinStreamlit Hub: share.streamlit.io/user/scalstein

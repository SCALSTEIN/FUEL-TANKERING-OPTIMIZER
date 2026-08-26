# ✈️ Fuel Burn & Economic Tankering Optimizer

A production-grade Flight Operations Engineering decision-support platform designed to model aerodynamic **cost-of-carry** and evaluate **economic fuel tankering** opportunities across regional and long-haul commercial airline networks.

---

## 📌 1. Operational Problem Statement
Fuel constitutes **25% to 40%** of an airline's Direct Operating Costs (DOC). Commercial carriers encounter substantial fuel price differentials across outstations due to local refinery access, transportation tariffs, and regional taxes. 

While carrying surplus fuel from a lower-cost origin station avoids purchasing expensive fuel downline, the aircraft incurs an **aerodynamic burn penalty** (carrying extra weight increases total lift-induced drag and engine fuel consumption). 

This tool dynamically evaluates the non-linear trade-off between fuel price spreads and flight burn penalties while strictly enforcing:
1. **Maximum Takeoff Weight (MTOW)**
2. **Maximum Landing Weight (MLW)**
3. **Maximum Zero Fuel Weight (MZFW)**
4. **Usable Fuel Tank Capacity & ICAO Fuel Reserve Mandates**

---

## 🧮 2. Mathematical Formulation

### Cost of Carry Penalty
$$\Delta M_{\text{burn}} = M_{\text{tanker}} \cdot \left( e^{\alpha \cdot T} - 1 \right)$$

*Where:*
* $\alpha$: Aerodynamic carry penalty coefficient ($0.035 - 0.045 \text{ hr}^{-1}$)
* $T$: Flight sector duration (hours)

### Net Economic Margin ($\Delta C$)
$$\Delta C = \left( M_{\text{tanker}} \cdot P_{\text{dest}} \right) - \left( (M_{\text{tanker}} + \Delta M_{\text{burn}}) \cdot P_{\text{origin}} \right)$$

*Where $P_{\text{origin}}, P_{\text{dest}}$ are in $\text{USD/kg}$. Tankering is executed if and only if $\Delta C > 0$ under all structural weight envelopes.*

---

## 🚀 3. Quickstart & Installation

### Local Setup
```bash
# Clone your repository
git clone https://github.com/<YOUR_USERNAME>/fuel-tankering-optimizer.git
cd fuel-tankering-optimizer

# Create and activate virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Run automated test suite
python -m pytest tests/

# Launch interactive Streamlit dashboard
streamlit run app.py
```

---

## 📊 4. Architecture & Features
* **Modular Performance Models:** Dynamic profiles for B737-800, E190, and B787-8.
* **Sensitivity Engine:** Instant parameter sweeps across station price deltas, headwinds, and payloads.
* **Structural Envelope Validation:** Automated clipping against MTOW, MLW, and MZFW.
* **Interactive UI:** Built with Streamlit and Plotly for intuitive dispatch decision-making.

---

## 👨‍💻 Author & Engineering Context
Developed as part of the Flight Operations Engineering Suite.

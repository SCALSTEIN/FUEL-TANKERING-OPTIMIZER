"""
Unit tests for Tankering Optimizer.
"""
from src.aircraft import load_aircraft_registry
from src.optimizer import TankeringOptimizer

def test_tankering_positive_differential():
    registry = load_aircraft_registry()
    ac = registry["B737-800"]
    optimizer = TankeringOptimizer(ac)
    
    # Origin cheap ($2.50), Dest expensive ($3.80)
    result = optimizer.evaluate_tankering(
        origin_icao="HKJK",
        dest_icao="KGL",
        origin_price_usd_per_gal=2.50,
        dest_price_usd_per_gal=3.80,
        payload_kg=12000,
        flight_time_hr=1.2,
        return_leg_fuel_demand_kg=4000
    )
    assert result.is_tankering_viable is True
    assert result.recommended_tanker_kg > 0
    assert result.net_economic_benefit_usd > 0
    assert result.takeoff_weight_kg <= ac.mtow_kg
    assert result.landing_weight_kg <= ac.mlw_kg

def test_tankering_negative_differential():
    registry = load_aircraft_registry()
    ac = registry["B737-800"]
    optimizer = TankeringOptimizer(ac)
    
    # Origin expensive ($3.50), Dest cheap ($2.40)
    result = optimizer.evaluate_tankering(
        origin_icao="HKJK",
        dest_icao="DXB",
        origin_price_usd_per_gal=3.50,
        dest_price_usd_per_gal=2.40,
        payload_kg=12000,
        flight_time_hr=4.8,
        return_leg_fuel_demand_kg=4000
    )
    assert result.is_tankering_viable is False
    assert result.recommended_tanker_kg == 0
    assert result.net_economic_benefit_usd == 0.0

if __name__ == "__main__":
    test_tankering_positive_differential()
    test_tankering_negative_differential()
    print("All Tankering Optimizer unit tests passed successfully!")

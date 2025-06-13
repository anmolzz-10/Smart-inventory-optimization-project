# simulator.py

import pandas as pd
from typing import Dict, List, Optional
from .core import InventorySimulator
from .data_loader import DataLoader
from .utils import convert_date_format


def run_simulation(
    product_id: str,
    start_date: str,
    end_date: str,
    demand_modifications: Optional[Dict[str, int]] = None,
    enable_risk: bool = False,
    holding_rate: float = 0.20,
    force_supplier_id: Optional[str] = None
) -> Dict:
    """
    Run a single what-if simulation for a specific product and configuration.
    
    Args:
        product_id: Product ID to simulate.
        start_date: Simulation start date in DD-MM-YYYY format.
        end_date: Simulation end date in DD-MM-YYYY format.
        demand_modifications: Dict of {date_str: new_demand_qty}.
        enable_risk: Whether to simulate supplier variability (lead time, fill rate).
        holding_rate: Annualized inventory holding rate (e.g., 0.20 = 20%).
        force_supplier_id: Override optimized supplier choice.

    Returns:
        Dict with keys:
            - "timeline": Daily simulation DataFrame.
            - "metrics": Summary performance KPIs.
            - "orders": All purchase orders placed.
    """
    # Convert dates to datetime objects
    start_dt = convert_date_format(start_date)
    end_dt = convert_date_format(end_date)

    # Prepare modified demand dictionary
    mods = {}
    if demand_modifications:
        mods = {convert_date_format(k): v for k, v in demand_modifications.items()}

    # Instantiate simulator with parameters
    simulator = InventorySimulator(product_id=product_id)

    # Run simulation
    results = simulator.run(
        start_date=start_dt,
        end_date=end_dt,
        demand_modifications=mods,
        holding_rate=holding_rate,
        enable_risk=enable_risk,
        force_supplier_id=force_supplier_id
    )
    return {
        "timeline": results["timeline"],
        "metrics": results["metrics"],
        "orders": simulator.order_mgr.get_pending_orders()
    }


def compare_scenarios(
    product_id: str,
    scenarios: List[Dict],
    start_date: str,
    end_date: str
) -> Dict[str, Dict]:
    """
    Run and compare multiple what-if scenarios for a given product.

    Args:
        product_id: Product ID to simulate.
        scenarios: List of scenario dicts. Each scenario can include:
            {
                "name": "Scenario Name",
                "demand_mods": {"10-04-2025": 200},
                "params": {
                    "enable_risk": True,
                    "holding_rate": 0.25,
                    "force_supplier_id": "S3"
                }
            }
        start_date: Simulation start date in DD-MM-YYYY format.
        end_date: Simulation end date in DD-MM-YYYY format.

    Returns:
        Dictionary mapping scenario name to performance metrics.
    """
    results = {}

    for scenario in scenarios:
        name = scenario.get("name", "Unnamed Scenario")
        demand_mods = scenario.get("demand_mods", {})
        params = scenario.get("params", {})

        output = run_simulation(
            product_id=product_id,
            start_date=start_date,
            end_date=end_date,
            demand_modifications=demand_mods,
            **params
        )

        results[name] = output["metrics"]

    return results


def save_scenario_results(results: Dict, filename: str):
    """
    Save simulation results to Parquet and JSON for dashboards or analysis.
    
    Args:
        results: Output dictionary from run_simulation().
        filename: Prefix for saved files (without extension).
    """
    results["timeline"].to_parquet(f"{filename}_timeline.parquet", index=False)

    pd.DataFrame([results["metrics"]]).to_json(
        f"{filename}_metrics.json",
        orient="records",
        indent=2
    )


def load_scenario_results(filename: str) -> Dict:
    """
    Load previously saved scenario results.
    
    Args:
        filename: Prefix used when saving results.

    Returns:
        Same format as run_simulation().
    """
    timeline = pd.read_parquet(f"{filename}_timeline.parquet")
    metrics = pd.read_json(f"{filename}_metrics.json").iloc[0].to_dict()

    return {"timeline": timeline, "metrics": metrics}
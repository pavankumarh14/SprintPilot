from fastapi import APIRouter
from app.data.seed_data import (
    SLIPPAGE_FORECAST, AT_RISK_ITEMS, AVG_VELOCITY, SPRINT_HISTORY,
    BURNDOWN, PROPOSED_SPRINT,
)
from app.services.monte_carlo import run_simulation

router = APIRouter()


@router.get("/slippage")
def get_slippage_forecast():
    """
    Get Monte-Carlo slippage forecast using live simulation.
    """
    # Get current state from burndown
    actuals = BURNDOWN.get("actual", [])
    sprint_dates = BURNDOWN.get("days", [])
    total_points = BURNDOWN.get("total_points", 0)
    
    # Find current day (last non-None actual value)
    current_day = 0
    remaining_pts = total_points
    for i, v in enumerate(actuals):
        if v is not None:
            current_day = i + 1
            remaining_pts = v
    
    # Calculate remaining days
    days_left = 10 - current_day
    
    if days_left > 0 and remaining_pts > 0:
        # Get remaining dates
        sprint_dates_remaining = sprint_dates[current_day:] if current_day < len(sprint_dates) else []
        
        # Run Monte Carlo simulation
        forecast = run_simulation(
            remaining_points=int(remaining_pts),
            days_left=days_left,
            sprint_history=SPRINT_HISTORY,
            sprint_dates=sprint_dates_remaining,
            burndown_actual=actuals,
        )
        
        # Determine trend
        if len(forecast) > 1:
            prob_first = forecast[0]["completion_probability"]
            prob_last = forecast[-1]["completion_probability"]
            trend = "declining" if prob_last < prob_first else "stable"
        else:
            trend = "stable"
        
        current_prob = forecast[0]["completion_probability"] if forecast else 0.5
    else:
        # Sprint complete or past end
        forecast = SLIPPAGE_FORECAST
        current_prob = 1.0 if remaining_pts == 0 else 0.0
        trend = "complete" if remaining_pts == 0 else "failed"
    
    return {
        "forecast": forecast,
        "current_day": current_day,
        "current_probability": current_prob,
        "trend": trend,
        "at_risk": AT_RISK_ITEMS,
    }


@router.get("/velocity")
def get_velocity_stats():
    velocities = [s["velocity"] for s in SPRINT_HISTORY]
    return {
        "average": round(AVG_VELOCITY, 1),
        "min": min(velocities),
        "max": max(velocities),
        "last_sprint": velocities[-1],
        "history": velocities,
    }

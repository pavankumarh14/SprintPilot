"""
SprintPilot — Monte-Carlo Slippage Forecast Engine
====================================================
Implemented ✅
"""
import random
import statistics
from typing import Optional


def build_velocity_distribution(
    sprint_history: list,
    sprint_days: int = 10,
) -> tuple:
    """
    Derive a per-day (mean, stdev) velocity from sprint history.
    """
    if not sprint_history:
        return (3.5, 1.0)  # Default fallback
    
    # Extract velocity values and convert to daily rate
    velocities = [s["velocity"] for s in sprint_history]
    daily_rates = [v / sprint_days for v in velocities]
    
    # Compute mean and sample standard deviation
    mean_daily = statistics.mean(daily_rates)
    
    # Handle case with only one sprint (stdev requires at least 2 values)
    if len(daily_rates) < 2:
        stdev_daily = mean_daily * 0.1  # Assume 10% variance
    else:
        stdev_daily = statistics.stdev(daily_rates)
    
    return (mean_daily, stdev_daily)


def project_remaining_points(
    burndown_actual: list,
    mean_daily: float,
) -> list:
    """
    For future days, project the expected remaining points using the mean burn rate.
    """
    if not burndown_actual:
        return []
    
    result = burndown_actual.copy()
    
    # Find the last non-None value and its index
    last_value = None
    last_index = -1
    for i, v in enumerate(result):
        if v is not None:
            last_value = v
            last_index = i
    
    if last_value is None or last_index == -1:
        return result
    
    # Project future values by subtracting mean daily burn
    for i in range(last_index + 1, len(result)):
        last_value = max(0.0, last_value - mean_daily)
        result[i] = round(last_value)
    
    return result


def run_simulation(
    remaining_points: int,
    days_left: int,
    sprint_history: list,
    sprint_dates: list,
    burndown_actual: list,
    n_simulations: int = 10_000,
) -> list:
    """
    Core Monte-Carlo engine. Run simulations to produce completion probabilities.
    """
    if days_left <= 0 or remaining_points <= 0:
        return []
    
    # Build velocity distribution from history
    mean_daily, stdev_daily = build_velocity_distribution(sprint_history, days_left)
    
    # Ensure stdev is positive
    stdev_daily = max(stdev_daily, 0.01)
    
    # Run simulations
    finish_days = []  # Record which day each simulation finished
    
    for _ in range(n_simulations):
        remaining = float(remaining_points)
        finished_on = days_left  # Default: didn't finish
        
        for day in range(days_left):
            # Sample daily burn from normal distribution
            daily_burn = max(0.0, random.gauss(mean_daily, stdev_daily))
            remaining = max(0.0, remaining - daily_burn)
            
            if remaining == 0:
                finished_on = day
                break
        
        finish_days.append(finished_on)
    
    # Calculate completion probability for each day
    result = []
    for day in range(days_left):
        # Count simulations that finished on or before this day
        finished_count = sum(1 for f in finish_days if f <= day)
        prob = finished_count / n_simulations
        result.append(round(prob, 2))
    
    # Project remaining points
    projected_points = project_remaining_points(burndown_actual, mean_daily)
    
    # Build output with dates
    output = []
    for day in range(days_left):
        output.append({
            "day": day + 1,
            "date": sprint_dates[day] if day < len(sprint_dates) else f"Day {day + 1}",
            "completion_probability": result[day],
            "remaining_points": projected_points[day] if day < len(projected_points) else 0,
        })
    
    return output

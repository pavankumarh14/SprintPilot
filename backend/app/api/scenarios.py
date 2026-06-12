"""
SprintPilot — What-If Scenario Simulator (Hackathon Feature)
============================================================

A powerful AI-powered scenario planning tool that lets teams instantly simulate
the impact of changes to their sprint without actually committing them.

Features:
- Drop tickets: See completion probability if specific tickets are removed
- Add capacity: Simulate adding part-time help or overtime
- Scope creep: Model impact of adding new mid-sprint tickets
- PTO simulation: See effect of team member unavailability
- Optimal plan: AI-suggests the best combination of tickets to complete
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Optional
from app.services.monte_carlo import build_velocity_distribution
from app.services.capacity_planner import build_sprint_plan, HOURS_PER_POINT
from app.data.seed_data import (
    SPRINT_HISTORY, BACKLOG_TICKETS, TEAM_MEMBERS, 
    LLM_ESTIMATES, DEPENDENCY_EDGES, BURNDOWN
)

router = APIRouter(tags=["scenarios"])

# -----------------------------------------------------------------------------
# Request/Response Models
# -----------------------------------------------------------------------------

class ScenarioRequest(BaseModel):
    action: str  # "drop", "add_capacity", "scope_creep", "pto", "optimize"
    parameters: dict
    

class TicketIdsRequest(BaseModel):
    ticket_ids: List[str]

class CapacityRequest(BaseModel):
    hours: int = 0
    member_id: Optional[str] = None

class PtoRequest(BaseModel):
    member_id: str
    days: int

class OptimizeRequest(BaseModel):
    target_probability: float = 0.8


class ScenarioResult(BaseModel):
    scenario_name: str
    completion_probability: float
    completion_probability_change: float
    days_to_complete: float
    capacity_remaining: float
    tickets_included: List[str]
    tickets_dropped: List[str]
    recommendation: str
    risk_level: str  # "low", "medium", "high"


# -----------------------------------------------------------------------------
# Core Scenario Engine
# -----------------------------------------------------------------------------

def calculate_completion_probability(remaining_points: int, days_left: int, 
                                    sprint_days: int = 10, n_simulations: int = 5000) -> float:
    """
    Run a quick Monte Carlo simulation for scenarios.
    """
    mean_daily, stdev_daily = build_velocity_distribution(SPRINT_HISTORY, sprint_days)
    
    is_invalid_mean = (
        mean_daily is None 
        or mean_daily != mean_daily  # NaN check
        or mean_daily <= 0
        or mean_daily == float('inf')
        or mean_daily == float('-inf')
    )
    if is_invalid_mean:
        return 1.0 if remaining_points <= 0 else 0.0
    
    is_invalid_stdev = (
        stdev_daily is None
        or (stdev_daily != stdev_daily)
        or stdev_daily <= 0
        or stdev_daily == float('inf')
    )
    stdev_daily = max(stdev_daily if not is_invalid_stdev else 0.01, 0.01)
    
    if not isinstance(remaining_points, (int, float)) or remaining_points < 0:
        remaining_points = 0
    if not isinstance(days_left, (int, float)) or days_left < 0:
        days_left = 0
    remaining_points = max(0, int(remaining_points))
    days_left = max(0, int(days_left))
    
    if remaining_points <= 0:
        return 1.0
    if days_left <= 0:
        return 0.0
    
    finish_count = 0
    for _ in range(n_simulations):
        remaining = float(remaining_points)
        for day in range(days_left):
            daily_burn = max(0.0, __import__('random').gauss(mean_daily, stdev_daily))
            remaining = max(0.0, remaining - daily_burn)
            if remaining == 0:
                finish_count += 1
                break
    
    return finish_count / n_simulations


def _safe_prob(value: float) -> float:
    if value is None or not isinstance(value, (int, float)):
        return 0.0
    if value != value:  # NaN
        return 0.0
    if value == float('inf') or value == float('-inf'):
        return 0.0
    return max(0.0, min(1.0, round(float(value), 4)))


def _risk_level(prob: float) -> str:
    if prob >= 0.8:
        return "low"
    elif prob >= 0.5:
        return "medium"
    else:
        return "high"


def _safe_scenario(name: str, prob: float, points: int, recommendation: str) -> dict:
    safe_prob = _safe_prob(prob)
    return {
        "name": name,
        "probability": safe_prob,
        "points": max(0, int(points)),
        "recommendation": recommendation or "",
        "risk": _risk_level(safe_prob),
    }


def get_current_sprint_state():
    """Get current state from burndown and board."""
    actuals = BURNDOWN.get("actual", [])
    total_points = BURNDOWN.get("total_points", 0)
    
    # Find current day and remaining points
    current_day = 0
    remaining_pts = total_points
    for i, v in enumerate(actuals):
        if v is not None:
            current_day = i + 1
            remaining_pts = v
    
    days_left = 10 - current_day
    return current_day, days_left, remaining_pts


# -----------------------------------------------------------------------------
# Scenario Handlers
# -----------------------------------------------------------------------------

@router.post("/drop", response_model=ScenarioResult)
def simulate_drop_tickets(payload: TicketIdsRequest):
    """
    Simulate what happens if specific tickets are dropped from the sprint.
    """
    ticket_ids = payload.ticket_ids
    current_day, days_left, remaining_pts = get_current_sprint_state()
    
    # Calculate points in dropped tickets
    dropped_points = sum(
        LLM_ESTIMATES.get(tid, {}).get("points", 0) 
        for tid in ticket_ids 
        if tid in LLM_ESTIMATES
    )
    
    new_remaining = max(0, remaining_pts - dropped_points)
    
    # Calculate original probability
    original_prob = calculate_completion_probability(remaining_pts, days_left)
    
    # Calculate new probability
    new_prob = calculate_completion_probability(new_remaining, days_left)
    
    # Determine all tickets that can now be included
    included = [
        t["id"] for t in BACKLOG_TICKETS 
        if t["id"] not in ticket_ids
    ]
    
    # Calculate days to complete based on velocity
    mean_daily, _ = build_velocity_distribution(SPRINT_HISTORY, 10)
    days_to_complete = new_remaining / max(mean_daily, 0.1) if mean_daily > 0 else days_left
    
    # Determine risk level
    if new_prob >= 0.8:
        risk_level = "low"
    elif new_prob >= 0.5:
        risk_level = "medium"
    else:
        risk_level = "high"
    
    # Generate recommendation
    if new_prob > original_prob + 0.1:
        recommendation = f"✅ Dropping these tickets significantly improves completion probability (+{round((new_prob-original_prob)*100)}%). Recommended if these tickets are not critical."
    elif new_prob > original_prob:
        recommendation = f"📈 Slight improvement in completion probability ({round((new_prob-original_prob)*100)}%). Drop these tickets if they're lower priority."
    else:
        recommendation = "ℹ️ Dropping these tickets provides minimal benefit. Consider keeping them or dropping different tickets."
    
    return ScenarioResult(
        scenario_name=f"Drop {len(ticket_ids)} ticket(s)",
        completion_probability=round(new_prob, 2),
        completion_probability_change=round(new_prob - original_prob, 2),
        days_to_complete=round(days_to_complete, 1),
        capacity_remaining=round((days_left * mean_daily) - new_remaining, 1),
        tickets_included=included[:10],  # Limit for response size
        tickets_dropped=ticket_ids,
        recommendation=recommendation,
        risk_level=risk_level,
    )


@router.post("/capacity", response_model=ScenarioResult)
def simulate_add_capacity(payload: CapacityRequest):
    """
    Simulate adding extra capacity (overtime or part-time help).
    """
    hours = payload.hours
    member_id = payload.member_id
    current_day, days_left, remaining_pts = get_current_sprint_state()
    
    # Original probability
    original_prob = calculate_completion_probability(remaining_pts, days_left)
    
    # Calculate effective days gained
    mean_daily, _ = build_velocity_distribution(SPRINT_HISTORY, 10)
    extra_burn = (hours / HOURS_PER_POINT) * mean_daily
    
    # Simulate with extra capacity (reduced effective remaining points)
    adjusted_remaining = max(0, remaining_pts - extra_burn)
    new_prob = calculate_completion_probability(adjusted_remaining, days_left)
    
    member_name = "team"
    if member_id:
        member = next((m for m in TEAM_MEMBERS if m["id"] == member_id), None)
        if member:
            member_name = member["name"]
    
    days_to_complete = adjusted_remaining / max(mean_daily, 0.1) if mean_daily > 0 else days_left
    
    risk_level = "low" if new_prob >= 0.8 else ("medium" if new_prob >= 0.5 else "high")
    
    if new_prob > original_prob + 0.15:
        recommendation = f"🚀 Adding {hours}h significantly helps! Completion probability jumps from {round(original_prob*100)}% to {round(new_prob*100)}%. Worth the extra effort."
    elif new_prob > original_prob:
        recommendation = f"💪 Modest improvement with {hours}h extra. Consider if {member_name} has capacity without burnout."
    else:
        recommendation = f"🤔 Extra {hours}h doesn't help much. The bottleneck might be dependencies, not capacity."
    
    return ScenarioResult(
        scenario_name=f"Add {hours}h capacity from {member_name}",
        completion_probability=round(new_prob, 2),
        completion_probability_change=round(new_prob - original_prob, 2),
        days_to_complete=round(days_to_complete, 1),
        capacity_remaining=round((days_left * mean_daily) - adjusted_remaining, 1),
        tickets_included=[t["id"] for t in BACKLOG_TICKETS][:10],
        tickets_dropped=[],
        recommendation=recommendation,
        risk_level=risk_level,
    )


@router.post("/scope-creep", response_model=ScenarioResult)
def simulate_scope_creep(payload: TicketIdsRequest):
    """
    Simulate adding new tickets mid-sprint (scope creep).
    """
    ticket_ids = payload.ticket_ids
    current_day, days_left, remaining_pts = get_current_sprint_state()
    
    # Calculate points in new tickets
    added_points = sum(
        LLM_ESTIMATES.get(tid, {}).get("points", 0) 
        for tid in ticket_ids 
        if tid in LLM_ESTIMATES
    )
    
    new_remaining = remaining_pts + added_points
    
    original_prob = calculate_completion_probability(remaining_pts, days_left)
    new_prob = calculate_completion_probability(new_remaining, days_left)
    
    mean_daily, _ = build_velocity_distribution(SPRINT_HISTORY, 10)
    days_to_complete = new_remaining / max(mean_daily, 0.1) if mean_daily > 0 else days_left
    
    risk_level = "low" if new_prob >= 0.8 else ("medium" if new_prob >= 0.5 else "high")
    
    if new_prob < 0.3:
        recommendation = f"❌ HIGH RISK! Adding these tickets drops completion probability to {round(new_prob*100)}%. Sprint will likely fail."
    elif new_prob < original_prob - 0.2:
        recommendation = f"⚠️ Adding these tickets significantly hurts the sprint (-{round((original_prob-new_prob)*100)}%). Only add if truly critical."
    else:
        recommendation = f"🟡 Adding these tickets has manageable impact. Completion probability: {round(new_prob*100)}%. Proceed with caution."
    
    return ScenarioResult(
        scenario_name=f"Add {len(ticket_ids)} tickets (scope creep)",
        completion_probability=round(new_prob, 2),
        completion_probability_change=round(new_prob - original_prob, 2),
        days_to_complete=round(days_to_complete, 1),
        capacity_remaining=round((days_left * mean_daily) - new_remaining, 1),
        tickets_included=[t["id"] for t in BACKLOG_TICKETS][:10] + ticket_ids,
        tickets_dropped=[],
        recommendation=recommendation,
        risk_level=risk_level,
    )


@router.post("/pto", response_model=ScenarioResult)
def simulate_pto(payload: PtoRequest):
    """
    Simulate the impact of a team member taking PTO.
    """
    member_id = payload.member_id
    days = payload.days
    current_day, days_left, remaining_pts = get_current_sprint_state()
    
    member = next((m for m in TEAM_MEMBERS if m["id"] == member_id), None)
    if not member:
        raise HTTPException(status_code=404, detail=f"Member {member_id} not found")
    
    # Estimate capacity reduction
    total_team_capacity = sum(m.get("capacity_hours", 40) for m in TEAM_MEMBERS)
    member_capacity = member.get("capacity_hours", 40)
    
    # They'll be out for 'days' days, so effective capacity lost
    # is proportional to days / sprint_days
    capacity_loss_ratio = (member_capacity / total_team_capacity) * (days / 10)
    
    # Adjust remaining points to account for reduced capacity
    adjusted_remaining = remaining_pts / max(0.1, 1 - capacity_loss_ratio)
    
    original_prob = calculate_completion_probability(remaining_pts, days_left)
    new_prob = calculate_completion_probability(adjusted_remaining, days_left)
    
    mean_daily, _ = build_velocity_distribution(SPRINT_HISTORY, 10)
    days_to_complete = adjusted_remaining / max(mean_daily, 0.1) if mean_daily > 0 else days_left
    
    risk_level = "low" if new_prob >= 0.8 else ("medium" if new_prob >= 0.5 else "high")
    
    if new_prob < 0.4:
        recommendation = f"🚨 CRITICAL: {member['name']} taking {days} days PTO severely impacts the sprint ({round(new_prob*100)}% probability). Consider reassigning their work or dropping tickets."
    elif new_prob < original_prob - 0.15:
        recommendation = f"⚠️ {member['name']} out for {days} days hurts the sprint significantly (-{round((original_prob-new_prob)*100)}%). Redistribute work among team."
    else:
        recommendation = f"✅ {member['name']} out for {days} days is manageable. Sprint completion: {round(new_prob*100)}%. Monitor progress carefully."
    
    # Find tickets assigned to this member that might need reassignment
    from app.data.seed_data import PROPOSED_SPRINT
    member_tickets = [
        t["id"] for t in PROPOSED_SPRINT.get("tickets", [])
        if t.get("assignee") == member_id
    ]
    
    return ScenarioResult(
        scenario_name=f"{member['name']} PTO ({days} days)",
        completion_probability=round(new_prob, 2),
        completion_probability_change=round(new_prob - original_prob, 2),
        days_to_complete=round(days_to_complete, 1),
        capacity_remaining=round((days_left * mean_daily) - adjusted_remaining, 1),
        tickets_included=[t["id"] for t in BACKLOG_TICKETS][:10],
        tickets_dropped=[],
        recommendation=recommendation,
        risk_level=risk_level,
    )


@router.post("/optimize", response_model=ScenarioResult)
def optimize_sprint(payload: OptimizeRequest):
    """
    AI-optimizes the sprint to hit a target completion probability.
    Suggests which tickets to drop or add.
    """
    target_probability = payload.target_probability
    current_day, days_left, remaining_pts = get_current_sprint_state()
    
    original_prob = calculate_completion_probability(remaining_pts, days_left)
    
    if original_prob >= target_probability:
        # We might be able to ADD tickets
        return ScenarioResult(
            scenario_name="Sprint already optimized",
            completion_probability=round(original_prob, 2),
            completion_probability_change=0.0,
            days_to_complete=round(remaining_pts / 3.5, 1),  # Approximate
            capacity_remaining=0.0,
            tickets_included=[t["id"] for t in BACKLOG_TICKETS][:10],
            tickets_dropped=[],
            recommendation=f"🎉 Sprint is already at {round(original_prob*100)}% completion probability (target: {round(target_probability*100)}%). No changes needed!",
            risk_level="low",
        )
    
    # Try to find the optimal set of tickets to drop
    mean_daily, _ = build_velocity_distribution(SPRINT_HISTORY, 10)
    target_points = mean_daily * days_left * 0.9  # 10% buffer
    
    # Sort tickets by points (smallest first - greedy approach)
    all_tickets = sorted(BACKLOG_TICKETS, key=lambda t: LLM_ESTIMATES.get(t["id"], {}).get("points", 999))
    
    # Binary search for which tickets to drop
    low, high = 0, len(all_tickets)
    best_result = None
    
    while low <= high:
        mid = (low + high) // 2
        kept_tickets = all_tickets[:mid]
        dropped_tickets = all_tickets[mid:]
        
        kept_points = sum(
            LLM_ESTIMATES.get(t["id"], {}).get("points", 0) 
            for t in kept_tickets
        )
        
        prob = calculate_completion_probability(kept_points, days_left)
        
        if prob >= target_probability:
            best_result = {
                "kept": kept_tickets,
                "dropped": dropped_tickets,
                "points": kept_points,
                "probability": prob,
            }
            # Try to keep more tickets
            high = mid - 1
        else:
            # Need to drop more
            low = mid + 1
    
    if best_result:
        days_to_complete = best_result["points"] / max(mean_daily, 0.1)
        
        return ScenarioResult(
            scenario_name=f"Optimized for {round(target_probability*100)}% probability",
            completion_probability=round(best_result["probability"], 2),
            completion_probability_change=round(best_result["probability"] - original_prob, 2),
            days_to_complete=round(days_to_complete, 1),
            capacity_remaining=round(target_points - best_result["points"], 1),
            tickets_included=[t["id"] for t in best_result["kept"]],
            tickets_dropped=[t["id"] for t in best_result["dropped"]],
            recommendation=f"✅ Optimized sprint plan: Drop {len(best_result['dropped'])} tickets to hit {round(best_result['probability']*100)}% completion probability. This gives you the best chance of success while keeping as much work as possible.",
            risk_level="low",
        )
    
    # Even dropping everything might not hit target
    return ScenarioResult(
        scenario_name="Cannot meet target",
        completion_probability=0.0,
        completion_probability_change=-round(original_prob, 2),
        days_to_complete=0.0,
        capacity_remaining=0.0,
        tickets_included=[],
        tickets_dropped=[t["id"] for t in BACKLOG_TICKETS],
        recommendation=f"❌ Even with no tickets, the sprint cannot meet the {round(target_probability*100)}% target given current capacity and remaining days. Consider extending sprint or adding capacity.",
        risk_level="high",
    )


@router.get("/compare")
def compare_scenarios():
    """
    Compare multiple scenarios side-by-side.
    Returns: [baseline, best_drop, best_capacity, optimized]
    """
    current_day, days_left, remaining_pts = get_current_sprint_state()
    
    scenarios = []
    
    # Baseline
    base_prob = calculate_completion_probability(remaining_pts, days_left)
    scenarios.append({
        "name": "Baseline (current)",
        "scenario_name": "Baseline (current)",
        "probability": _safe_prob(base_prob),
        "completion_probability": _safe_prob(base_prob),
        "completion_probability_change": 0.0,
        "points": remaining_pts,
        "recommendation": "Current sprint plan",
        "risk": _risk_level(base_prob) if _safe_prob(base_prob) == base_prob else _risk_level(_safe_prob(base_prob)),
        "risk_level": _risk_level(base_prob) if _safe_prob(base_prob) == base_prob else _risk_level(_safe_prob(base_prob)),
    })
    
    # Drop riskiest ticket (assumed to be highest point value)
    riskiest_id = max(
        LLM_ESTIMATES.keys(),
        key=lambda k: LLM_ESTIMATES.get(k, {}).get("points", 0),
        default=None
    )
    if riskiest_id:
        drop_result = simulate_drop_tickets(TicketIdsRequest(ticket_ids=[riskiest_id]))
        drop_prob = _safe_prob(drop_result.completion_probability)
        scenarios.append({
            "name": f"Drop {riskiest_id}",
            "scenario_name": f"Drop {riskiest_id}",
            "probability": drop_prob,
            "completion_probability": drop_prob,
            "completion_probability_change": round(drop_prob - _safe_prob(base_prob), 4),
            "points": max(0, remaining_pts - LLM_ESTIMATES.get(riskiest_id, {}).get("points", 0)),
            "recommendation": drop_result.recommendation,
            "risk": _risk_level(drop_prob),
            "risk_level": _risk_level(drop_prob),
        })
    
    # Add capacity
    capacity_result = simulate_add_capacity(CapacityRequest(hours=16))  # 2 extra days
    cap_prob = _safe_prob(capacity_result.completion_probability)
    scenarios.append({
        "name": "Add 16h capacity",
        "scenario_name": "Add 16h capacity",
        "probability": cap_prob,
        "completion_probability": cap_prob,
        "completion_probability_change": round(cap_prob - _safe_prob(base_prob), 4),
        "points": remaining_pts,
        "recommendation": capacity_result.recommendation,
        "risk": _risk_level(cap_prob),
        "risk_level": _risk_level(cap_prob),
    })
    
    # Optimized
    optimized = optimize_sprint(OptimizeRequest(target_probability=0.8))
    opt_prob = _safe_prob(optimized.completion_probability)
    scenarios.append({
        "name": "AI-Optimized Plan",
        "scenario_name": "AI-Optimized Plan",
        "probability": opt_prob,
        "completion_probability": opt_prob,
        "completion_probability_change": round(opt_prob - _safe_prob(base_prob), 4),
        "points": max(0, sum(
            LLM_ESTIMATES.get(tid, {}).get("points", 0) 
            for tid in optimized.tickets_included
        )),
        "recommendation": optimized.recommendation,
        "risk": _risk_level(opt_prob),
        "risk_level": _risk_level(opt_prob),
    })
    
    safe_scenarios = [s for s in scenarios]
    if not safe_scenarios:
        safe_scenarios = [{
            "name": "Baseline (fallback)",
            "scenario_name": "Baseline (fallback)",
            "probability": 0.5,
            "completion_probability": 0.5,
            "completion_probability_change": 0.0,
            "points": remaining_pts,
            "recommendation": "Current sprint plan",
            "risk": "medium",
            "risk_level": "medium",
        }]
    
    return {
        "scenarios": safe_scenarios,
        "best_scenario": max(safe_scenarios, key=lambda s: s["probability"])["name"],
    }

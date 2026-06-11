"""
SprintPilot — Capacity-Aware Sprint Planner
============================================
Implemented ✅
"""
from typing import Optional
import logging

logger = logging.getLogger(__name__)
HOURS_PER_POINT: float = 8.0

ROLE_LABEL_MAP: dict = {
    "Backend Engineer":   ["backend", "security", "performance", "notifications", "integration"],
    "Frontend Engineer":  ["frontend", "ux", "analytics"],
    "AI / ML Engineer":   ["ai", "forecasting"],
    "QA Engineer":        ["qa"],
    "Full-stack Engineer": [],   # catch-all
}


def topological_sort(ticket_ids: list, edges: list) -> list:
    """
    Return ticket IDs in topological order (all blockers before their dependents).
    Uses Kahn's algorithm (BFS).
    """
    # Build adjacency list and in-degree count
    adj = {tid: [] for tid in ticket_ids}
    indeg = {tid: 0 for tid in ticket_ids}
    
    for e in edges:
        from_id = e["from"]
        to_id = e["to"]
        if from_id in adj and to_id in indeg:
            adj[from_id].append(to_id)
            indeg[to_id] += 1
    
    # Initialize queue with all nodes where indeg == 0
    from collections import deque
    queue = deque([tid for tid in ticket_ids if indeg[tid] == 0])
    result = []
    
    while queue:
        u = queue.popleft()
        result.append(u)
        
        for v in adj[u]:
            indeg[v] -= 1
            if indeg[v] == 0:
                queue.append(v)
    
    # If there are remaining nodes, we've detected a cycle
    if len(result) < len(ticket_ids):
        remaining = [tid for tid in ticket_ids if tid not in result]
        logger.warning(f"Cycle detected in dependency graph. Remaining: {remaining}")
        # Append remaining nodes in arbitrary order
        result.extend(remaining)
    
    return result


def role_score(member_role: str, ticket_labels: list) -> int:
    """
    Score how well a member's role matches a ticket's labels (higher is better).
    """
    preferred_labels = ROLE_LABEL_MAP.get(member_role, [])
    if not preferred_labels:
        return 0
    
    # Count matching labels
    matches = sum(1 for label in ticket_labels if label.lower() in [pl.lower() for pl in preferred_labels])
    return matches


def assign_to_member(
    ticket: dict,
    estimates: dict,
    members: list,
    used_hours: dict,
) -> Optional[str]:
    """
    Choose the best available team member for a single ticket.
    """
    ticket_id = ticket["id"]
    
    # Look up points for this ticket
    est = estimates.get(ticket_id, {})
    points = est.get("points", 1)
    hours_needed = points * HOURS_PER_POINT
    
    # Filter to eligible members (have capacity)
    eligible = []
    for m in members:
        member_id = m["id"]
        capacity = m.get("capacity_hours", 0)
        already_used = used_hours.get(member_id, 0)
        remaining_capacity = capacity - already_used
        
        if remaining_capacity >= hours_needed:
            score = role_score(m["role"], ticket.get("labels", []))
            eligible.append({
                "id": member_id,
                "role": m["role"],
                "score": score,
                "remaining": remaining_capacity,
            })
    
    if not eligible:
        return None
    
    # Sort by: 1) role_score descending, 2) remaining capacity descending
    eligible.sort(key=lambda x: (-x["score"], -x["remaining"]))
    
    return eligible[0]["id"]


def build_sprint_plan(
    backlog_tickets: list,
    estimates: dict,
    team_members: list,
    dependency_edges: list,
    sprint_number: int,
    start_date: str,
    end_date: str,
    sprint_days: int = 10,
) -> dict:
    """
    Assemble the full sprint plan with capacity-aware assignment.
    """
    # Get all ticket IDs
    ticket_ids = [t["id"] for t in backlog_tickets]
    
    # Topologically sort
    sorted_ids = topological_sort(ticket_ids, dependency_edges)
    
    # Create ticket lookup
    ticket_lookup = {t["id"]: t for t in backlog_tickets}
    
    # Initialize state
    used_hours = {m["id"]: 0.0 for m in team_members}
    member_lookup = {m["id"]: m for m in team_members}
    finish_day = {}
    planned = []
    deferred = []
    
    # Build adjacency for looking up blockers
    edge_lookup = {}
    for e in dependency_edges:
        if e["to"] not in edge_lookup:
            edge_lookup[e["to"]] = []
        edge_lookup[e["to"]].append(e["from"])
    
    # Assign tickets in dependency order
    for ticket_id in sorted_ids:
        ticket = ticket_lookup.get(ticket_id)
        if not ticket:
            continue
        
        # Try to assign
        assignee = assign_to_member(ticket, estimates, team_members, used_hours)
        
        if assignee is None:
            deferred.append(ticket_id)
            continue
        
        # Update used hours
        pts = estimates.get(ticket_id, {}).get("points", 1)
        used_hours[assignee] += pts * HOURS_PER_POINT
        
        # Calculate start day based on blockers
        blockers = edge_lookup.get(ticket_id, [])
        if blockers:
            max_finish = max(finish_day.get(b, 0) for b in blockers)
            sprint_day_start = min(max_finish + 1, sprint_days)
        else:
            sprint_day_start = 1
        
        # Clamp to sprint bounds
        sprint_day_start = max(1, min(sprint_day_start, sprint_days))
        
        # Calculate estimated days
        estimated_days = max(1, round(pts * HOURS_PER_POINT / 8))
        
        # Record finish day for this ticket
        finish_day[ticket_id] = min(sprint_day_start + estimated_days - 1, sprint_days)
        
        planned.append({
            "id": ticket_id,
            "assignee": assignee,
            "sprint_day_start": sprint_day_start,
            "estimated_days": estimated_days,
            "status": "todo",
        })
    
    total_capacity_points = sum(
        estimates.get(t["id"], {}).get("points", 0) for t in planned
    )
    
    # Build deferred notes
    if deferred:
        notes = f"Deferred {len(deferred)} tickets due to capacity constraints: {', '.join(deferred)}"
    else:
        notes = "All tickets scheduled successfully."
    
    return {
        "sprint_number": sprint_number,
        "start_date": start_date,
        "end_date": end_date,
        "total_capacity_points": total_capacity_points,
        "tickets": planned,
        "deferred": deferred,
        "notes": notes,
    }

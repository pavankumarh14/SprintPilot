"""
SprintPilot — Implicit Dependency Detector
===========================================
Implemented ✅
"""
import asyncio
import json
import logging
from typing import Optional

from app.services.llm import call_llm

logger = logging.getLogger(__name__)
MAX_CONCURRENT = 5

CLASSIFY_SYSTEM = """You are a software dependency analyser.
Given two Jira-style tickets A and B, decide whether A BLOCKS B.
A blocks B when B cannot begin (or cannot be merged) until A is complete.

Respond with ONLY valid JSON — no markdown, no extra keys:
{
  "blocks": true | false,
  "confidence": 0.0-1.0,
  "reason": "<one concise sentence>"
}"""


def has_path(adj: dict, start: str, goal: str) -> bool:
    """
    Depth-first reachability check used for cycle detection.
    """
    if start == goal:
        return True
    if start not in adj or not adj[start]:
        return False
    
    visited = set()
    stack = [start]
    
    while stack:
        node = stack.pop()
        if node == goal:
            return True
        if node in visited:
            continue
        visited.add(node)
        if node in adj:
            for neighbor in adj[node]:
                if neighbor not in visited:
                    stack.append(neighbor)
    
    return False


async def classify_pair(
    ticket_a: dict,
    ticket_b: dict,
    api_key: Optional[str] = None,
    confidence_threshold: float = 0.7,
) -> Optional[dict]:
    """
    Ask the LLM whether ticket_a blocks ticket_b.
    """
    # Build user message
    user_msg = f"""Ticket A: {ticket_a['id']} — {ticket_a['title']}
Description: {ticket_a.get('description', 'No description')}
Labels: {', '.join(ticket_a.get('labels', []))}

Ticket B: {ticket_b['id']} — {ticket_b['title']}
Description: {ticket_b.get('description', 'No description')}
Labels: {', '.join(ticket_b.get('labels', []))}

Does A block B?"""
    
    try:
        raw, is_real = await call_llm(CLASSIFY_SYSTEM, user_msg, api_key=api_key)
        
        if not is_real:
            return None
        
        # Strip markdown fences and parse JSON
        cleaned = raw.strip()
        if cleaned.startswith("```json"):
            cleaned = cleaned[7:]
        elif cleaned.startswith("```"):
            cleaned = cleaned[3:]
        cleaned = cleaned.rstrip("```").strip()
        
        parsed = json.loads(cleaned)
        
        if parsed.get("blocks") is True and parsed.get("confidence", 0.0) >= confidence_threshold:
            return {
                "from": ticket_a["id"],
                "to": ticket_b["id"],
                "reason": parsed["reason"],
                "source": "llm",
            }
        
        return None
    
    except (json.JSONDecodeError, KeyError) as e:
        logger.warning(f"Failed to parse LLM response: {e}")
        return None
    except Exception as e:
        logger.error(f"Error in classify_pair: {e}")
        return None


async def detect_implicit_dependencies(
    tickets: list,
    explicit_edges: list,
    api_key: Optional[str] = None,
) -> list:
    """
    Orchestrate all pair classifications and merge with explicit edges.
    """
    # If no API key, return explicit edges unchanged (mock fallback)
    if not api_key:
        return explicit_edges
    
    # Build set of already-known (from, to) pairs from explicit edges
    known_pairs = {(e["from"], e["to"]) for e in explicit_edges}
    
    # Build adjacency list from explicit edges for cycle detection
    adj = {}
    for e in explicit_edges:
        if e["from"] not in adj:
            adj[e["from"]] = []
        adj[e["from"]].append(e["to"])
    
    # Create semaphore for concurrency control
    sem = asyncio.Semaphore(MAX_CONCURRENT)
    
    # Collect all candidate pairs (all ordered pairs not already known)
    async def check_pair(a, b):
        if a["id"] == b["id"]:
            return None
        if (a["id"], b["id"]) in known_pairs:
            return None
        
        async with sem:
            return await classify_pair(a, b, api_key=api_key)
    
    # Create all tasks
    tasks = []
    for a in tickets:
        for b in tickets:
            tasks.append(check_pair(a, b))
    
    # Run all tasks concurrently (limited by semaphore)
    results = await asyncio.gather(*tasks, return_exceptions=True)
    
    # Collect and validate non-None edges
    inferred_edges = []
    for result in results:
        if isinstance(result, Exception):
            logger.warning(f"Task failed: {result}")
            continue
        
        if result is None:
            continue
        
        # Check if adding this edge would create a cycle
        from_id = result["from"]
        to_id = result["to"]
        
        # Check if to_id can reach from_id (adding edge would create cycle)
        if has_path(adj, to_id, from_id):
            logger.info(f"Discarding {from_id} → {to_id}: would create cycle")
            continue
        
        # Add edge to adjacency list result
        if from_id not in adj:
            adj[from_id] = []
        adj[from_id].append(to_id)
        inferred_edges.append(result)
    
    # Return explicit + inferred edges
    return explicit_edges + inferred_edges

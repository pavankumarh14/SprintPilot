"""
LLM service for SprintPilot.

Priority:
  1. API key passed per-request via X-LLM-Key header (supports any bearer key)
  2. OPENAI_API_KEY environment variable (OpenAI)
  3. ANTHROPIC_API_KEY environment variable (Anthropic / Claude)
  4. Mock fallback — returns pre-computed seed data (no key required)
"""

import os
import json
import logging
import httpx
from typing import Optional

logger = logging.getLogger(__name__)


def _detect_provider(key: str) -> str:
    """Return 'anthropic' or 'openai' based on key prefix."""
    if key.startswith("sk-ant-"):
        return "anthropic"
    return "openai"


def resolve_key(request_key: Optional[str] = None) -> Optional[str]:
    """
    Return the first available API key, or None if none configured.
    Order: request header → OPENAI_API_KEY → ANTHROPIC_API_KEY
    """
    if request_key:
        return request_key.strip()
    k = os.getenv("OPENAI_API_KEY") or os.getenv("ANTHROPIC_API_KEY")
    return k.strip() if k else None


def has_real_key(request_key: Optional[str] = None) -> bool:
    return resolve_key(request_key) is not None


async def _call_openai(key: str, system: str, user: str, max_tokens: int = 512) -> str:
    headers = {
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json",
    }
    body = {
        "model": "gpt-4o-mini",
        "max_tokens": max_tokens,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user",   "content": user},
        ],
    }
    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.post(
            "https://api.openai.com/v1/chat/completions",
            headers=headers,
            json=body,
        )
        resp.raise_for_status()
        data = resp.json()
        return data["choices"][0]["message"]["content"]


async def _call_anthropic(key: str, system: str, user: str, max_tokens: int = 512) -> str:
    headers = {
        "x-api-key": key,
        "anthropic-version": "2023-06-01",
        "Content-Type": "application/json",
    }
    body = {
        "model": "claude-haiku-4-5-20251001",
        "max_tokens": max_tokens,
        "system": system,
        "messages": [{"role": "user", "content": user}],
    }
    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.post(
            "https://api.anthropic.com/v1/messages",
            headers=headers,
            json=body,
        )
        resp.raise_for_status()
        data = resp.json()
        return data["content"][0]["text"]


async def call_llm(
    system: str,
    user: str,
    api_key: Optional[str] = None,
    max_tokens: int = 512,
) -> tuple[str, bool]:
    """
    Call the LLM and return (text, is_real).
    is_real=True means a real API was used; False means mock data.
    """
    key = resolve_key(api_key)
    if not key:
        return "", False  # caller should use mock

    provider = _detect_provider(key)
    try:
        if provider == "anthropic":
            text = await _call_anthropic(key, system, user, max_tokens)
        else:
            text = await _call_openai(key, system, user, max_tokens)
        return text, True
    except httpx.HTTPStatusError as e:
        logger.warning("LLM API error %s: %s — falling back to mock", e.response.status_code, e.response.text[:200])
        return "", False
    except Exception as e:
        logger.warning("LLM call failed (%s) — falling back to mock", e)
        return "", False


ESTIMATE_SYSTEM = """You are an agile estimation assistant.
Given a ticket description and a list of similar completed tickets (with story points and cycle days),
estimate the story points for the new ticket.

Respond with ONLY valid JSON in exactly this shape:
{
  "points": <integer>,
  "low": <integer>,
  "high": <integer>,
  "rationale": "<one sentence>"
}
No markdown, no extra keys."""


async def estimate_ticket(
    ticket: dict,
    similar_tickets: list[dict],
    api_key: Optional[str] = None,
    mock_estimate: Optional[dict] = None,
) -> dict:
    """
    Return an estimate dict. Falls back to mock_estimate when no key available
    or if the LLM call fails.
    """
    # Build similar_summary
    if similar_tickets:
        similar_summary = "\n".join([
            f"- {st.get('id', 'N/A')}: \"{st.get('title', 'Untitled')}\" — {st.get('story_points', 'N/A')} pts, {st.get('cycle_days', 'N/A')} days"
            for st in similar_tickets
        ])
    else:
        similar_summary = "No similar tickets found."
    
    # Build user message
    user_msg = f"""Ticket: {ticket['id']} — "{ticket['title']}"
Description: {ticket.get('description', 'No description')}

Similar completed tickets:
{similar_summary}

Estimate story points for this ticket."""
    
    try:
        raw, is_real = await call_llm(ESTIMATE_SYSTEM, user_msg, api_key=api_key, max_tokens=256)
        
        if not is_real:
            return {**(mock_estimate or {}), "source": "mock"}
        
        # Strip markdown fences and parse JSON
        cleaned = raw.strip()
        if cleaned.startswith("```json"):
            cleaned = cleaned[7:]
        elif cleaned.startswith("```"):
            cleaned = cleaned[3:]
        cleaned = cleaned.rstrip("```").strip()
        
        parsed = json.loads(cleaned)
        
        # Validate required fields
        required = ["points", "low", "high", "rationale"]
        if all(k in parsed for k in required):
            return {**parsed, "source": "llm"}
        
        # Missing fields, use mock
        logger.warning(f"LLM estimate missing fields: {parsed}")
        return {**(mock_estimate or {}), "source": "mock"}
    
    except (json.JSONDecodeError, Exception) as e:
        logger.warning(f"Error parsing LLM estimate: {e}. Raw: {raw if 'raw' in locals() else 'N/A'}")
        return {**(mock_estimate or {}), "source": "mock"}


DIGEST_SYSTEM = """You are a scrum master AI assistant writing a daily sprint digest.
Given the current sprint state (tickets, statuses, burndown, at-risk items),
write a concise standup digest in Markdown.

Structure it exactly as:
**SprintPilot Daily Digest — Day {day}**

🟢 **Completed yesterday**
...

🔵 **In progress today**
...

🔴 **Blockers**
...

⚠️ **SprintPilot alert**
...

Be specific and factual. Use the data provided. Keep it under 300 words."""


async def generate_digest(
    sprint_state: dict,
    burndown: dict,
    at_risk: list[dict],
    day: int,
    date_str: str,
    api_key: Optional[str] = None,
    mock_digest: Optional[str] = None,
) -> tuple[str, str]:
    """
    Return (digest_text, source) where source is 'llm' or 'mock'.
    """
    key = resolve_key(api_key)
    if not key:
        return mock_digest or "", "mock"
    
    # Build tickets summary
    tickets = sprint_state.get("tickets", [])
    if tickets:
        tickets_summary = "\n".join([
            f"  - {t['id']} ({t.get('title', 'Untitled')}): status={t.get('status', 'unknown')}, assignee={t.get('assignee', 'unassigned')}, pts={t.get('points', 'N/A')}"
            for t in tickets
        ])
    else:
        tickets_summary = "  No tickets in sprint."
    
    # Build at-risk summary
    if at_risk:
        at_risk_summary = "\n".join([
            f"  - {item['ticket_id']} [{item.get('risk_level', 'UNKNOWN')}]: {item.get('reason', 'No reason')}"
            for item in at_risk
        ])
    else:
        at_risk_summary = "  None"
    
    # Find remaining points
    total_points = burndown.get("total_points", 0)
    actuals = burndown.get("actual", [])
    remaining = total_points
    for v in reversed(actuals):
        if v is not None:
            remaining = v
            break
    
    sprint_number = sprint_state.get("sprint_number", "N/A")
    
    # Build user message
    user_msg = f"""Sprint {sprint_number}, Day {day} ({date_str})
Remaining points: {remaining} of {total_points}

Tickets:
{tickets_summary}

At-risk:
{at_risk_summary}

Write the daily standup digest."""
    
    try:
        raw, is_real = await call_llm(DIGEST_SYSTEM, user_msg, api_key=api_key, max_tokens=512)
        
        if not is_real:
            return mock_digest or "", "mock"
        
        return raw.strip(), "llm"
    
    except Exception as e:
        logger.warning(f"Error generating digest: {e}")
        return mock_digest or "", "mock"

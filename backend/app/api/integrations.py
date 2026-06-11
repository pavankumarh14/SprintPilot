"""
SprintPilot — Integration Status & Sync Endpoints
===================================================
Implemented ✅

GET  /api/integrations/status      — which integrations are configured
POST /api/integrations/config      — save integration config for this session
POST /api/integrations/jira/sync   — pull tickets + sprint history from Jira
POST /api/integrations/github/sync — pull issues from GitHub
POST /api/integrations/slack/test  — send a test Slack message
"""
import os
import logging
from fastapi import APIRouter
from pydantic import BaseModel
from typing import Optional

from app.services import jira_client, github_client, notifier

logger = logging.getLogger(__name__)
router = APIRouter()

# In-memory config store — holds credentials saved via POST /api/integrations/config.
# Treated the same as env vars: env vars take precedence; these are the fallback.
_config: dict = {}


def _get(key: str) -> str:
    """Return env var value, falling back to in-memory config."""
    return os.getenv(key) or _config.get(key, "")


# ── Request models ──────────────────────────────────────────────────────────

class IntegrationConfig(BaseModel):
    jira_url:          Optional[str] = None
    jira_email:        Optional[str] = None
    jira_api_token:    Optional[str] = None
    jira_project_key:  Optional[str] = None
    jira_board_id:     Optional[str] = None
    slack_webhook_url: Optional[str] = None
    slack_bot_token:   Optional[str] = None
    github_token:      Optional[str] = None
    github_owner:      Optional[str] = None
    github_repo:       Optional[str] = None
    linear_api_key:    Optional[str] = None
    linear_team_id:    Optional[str] = None


# ── Endpoints ───────────────────────────────────────────────────────────────

@router.get("/status")
def get_integration_status():
    """Return which integrations are fully configured (env vars or saved config)."""
    return {
        "jira": {
            "configured": all([
                _get("JIRA_URL"), _get("JIRA_EMAIL"),
                _get("JIRA_API_TOKEN"), _get("JIRA_PROJECT_KEY"),
            ]),
            "fields": {
                "JIRA_URL":          bool(_get("JIRA_URL")),
                "JIRA_EMAIL":        bool(_get("JIRA_EMAIL")),
                "JIRA_API_TOKEN":    bool(_get("JIRA_API_TOKEN")),
                "JIRA_PROJECT_KEY":  bool(_get("JIRA_PROJECT_KEY")),
                "JIRA_BOARD_ID":     bool(_get("JIRA_BOARD_ID")),
            },
        },
        "slack": {
            "configured": bool(_get("SLACK_WEBHOOK_URL") or _get("SLACK_BOT_TOKEN")),
            "fields": {
                "SLACK_WEBHOOK_URL": bool(_get("SLACK_WEBHOOK_URL")),
                "SLACK_BOT_TOKEN":   bool(_get("SLACK_BOT_TOKEN")),
            },
        },
        "github": {
            "configured": all([
                _get("GITHUB_TOKEN"), _get("GITHUB_OWNER"), _get("GITHUB_REPO"),
            ]),
            "fields": {
                "GITHUB_TOKEN": bool(_get("GITHUB_TOKEN")),
                "GITHUB_OWNER": bool(_get("GITHUB_OWNER")),
                "GITHUB_REPO":  bool(_get("GITHUB_REPO")),
            },
        },
        "linear": {
            "configured": all([_get("LINEAR_API_KEY"), _get("LINEAR_TEAM_ID")]),
            "fields": {
                "LINEAR_API_KEY": bool(_get("LINEAR_API_KEY")),
                "LINEAR_TEAM_ID": bool(_get("LINEAR_TEAM_ID")),
            },
        },
    }


@router.post("/config")
def save_integration_config(cfg: IntegrationConfig):
    """
    Persist integration credentials in-memory for this server session.
    Env vars always take precedence over values saved here.
    """
    mapping = {
        "JIRA_URL":          cfg.jira_url,
        "JIRA_EMAIL":        cfg.jira_email,
        "JIRA_API_TOKEN":    cfg.jira_api_token,
        "JIRA_PROJECT_KEY":  cfg.jira_project_key,
        "JIRA_BOARD_ID":     cfg.jira_board_id,
        "SLACK_WEBHOOK_URL": cfg.slack_webhook_url,
        "SLACK_BOT_TOKEN":   cfg.slack_bot_token,
        "GITHUB_TOKEN":      cfg.github_token,
        "GITHUB_OWNER":      cfg.github_owner,
        "GITHUB_REPO":       cfg.github_repo,
        "LINEAR_API_KEY":    cfg.linear_api_key,
        "LINEAR_TEAM_ID":    cfg.linear_team_id,
    }
    for key, val in mapping.items():
        if val is not None:
            _config[key] = val
    return {"saved": True, "status": get_integration_status()}


@router.post("/jira/sync")
async def sync_jira():
    """
    Pull open issues and sprint history from Jira, upsert into seed data.
    """
    from app.data.seed_data import BACKLOG_TICKETS, SPRINT_HISTORY
    
    # Temporarily update environment for this session
    for key in _config:
        os.environ[key] = _config.get(key, "")
    
    try:
        tickets = await jira_client.fetch_issues()
        history = await jira_client.fetch_sprint_history()
        
        # Merge into seed data (in-memory for this session)
        synced_count = 0
        for t in tickets:
            # Check if already exists
            existing = [bt for bt in BACKLOG_TICKETS if bt["id"] == t["id"]]
            if not existing:
                BACKLOG_TICKETS.append(t)
                synced_count += 1
        
        # Merge sprint history
        sprint_synced = 0
        for h in history:
            existing = [sh for sh in SPRINT_HISTORY if sh.get("sprint") == h.get("sprint")]
            if not existing:
                SPRINT_HISTORY.append(h)
                sprint_synced += 1
        
        return {
            "synced_tickets": synced_count,
            "synced_sprints": sprint_synced,
            "total_tickets": len(tickets),
            "total_sprints": len(history),
        }
    
    except Exception as e:
        logger.exception("Jira sync failed")
        return {"error": str(e), "synced_tickets": 0, "synced_sprints": 0}


@router.post("/github/sync")
async def sync_github():
    """
    Pull open issues from GitHub, upsert into BACKLOG_TICKETS.
    """
    from app.data.seed_data import BACKLOG_TICKETS
    
    # Temporarily update environment for this session
    for key in _config:
        os.environ[key] = _config.get(key, "")
    
    try:
        issues = await github_client.fetch_issues()
        
        # Merge into seed data (in-memory for this session)
        synced_count = 0
        for i in issues:
            # Check if already exists
            existing = [bt for bt in BACKLOG_TICKETS if bt["id"] == i["id"]]
            if not existing:
                BACKLOG_TICKETS.append(i)
                synced_count += 1
        
        return {
            "synced": synced_count,
            "total": len(issues),
        }
    
    except Exception as e:
        logger.exception("GitHub sync failed")
        return {"error": str(e), "synced": 0, "total": 0}


@router.post("/slack/test")
async def test_slack():
    """
    Send a test message to the configured Slack channel.
    """
    # Temporarily update environment for this session
    for key in _config:
        os.environ[key] = _config.get(key, "")
    
    import httpx
    
    webhook_url = os.getenv("SLACK_WEBHOOK_URL") or _config.get("SLACK_WEBHOOK_URL")
    
    if not webhook_url:
        return {"ok": False, "error": "SLACK_WEBHOOK_URL not configured"}
    
    try:
        payload = {
            "blocks": [
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": "*SprintPilot* connected ✅\n\nThis is a test message from your SprintPilot integration."
                    }
                }
            ]
        }
        
        async with httpx.AsyncClient() as client:
            resp = await client.post(webhook_url, json=payload)
        
        return {"ok": resp.status_code == 200, "status_code": resp.status_code}
    
    except Exception as e:
        logger.exception("Slack test failed")
        return {"ok": False, "error": str(e)}

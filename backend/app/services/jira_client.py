"""
SprintPilot — Jira Cloud API Client
=====================================
Implemented ✅

Pull tickets and sprint history from a Jira Cloud project so SprintPilot
can run analysis on real data instead of seed data.
"""
import os
import base64
import logging
import httpx
from typing import Optional

logger = logging.getLogger(__name__)


def _auth_header() -> str:
    email = os.getenv("JIRA_EMAIL", "")
    token = os.getenv("JIRA_API_TOKEN", "")
    encoded = base64.b64encode(f"{email}:{token}".encode()).decode()
    return f"Basic {encoded}"


def _map_status(status_name: str) -> str:
    """Map Jira status names to SprintPilot status values."""
    status_map = {
        "To Do": "todo",
        "In Progress": "in_progress",
        "In Review": "review",
        "Done": "done",
        "Closed": "done",
        "Resolved": "done",
    }
    return status_map.get(status_name, "todo")


def is_configured() -> bool:
    return all([
        os.getenv("JIRA_URL"),
        os.getenv("JIRA_EMAIL"),
        os.getenv("JIRA_API_TOKEN"),
        os.getenv("JIRA_PROJECT_KEY"),
    ])


def _extract_story_points(fields: dict) -> int:
    """Extract story points from Jira custom field (if present)."""
    # Common story point field names in Jira
    for key in ["customfield_10016", "customfield_10004", "customfield_10003", "story_points", "customfield_10000"]:
        if key in fields and fields[key] is not None:
            try:
                return int(fields[key])
            except (ValueError, TypeError):
                continue
    return 0


async def fetch_issues(
    project_key: Optional[str] = None,
    max_results: int = 50,
) -> list:
    """
    Pull open issues from a Jira project and return them in SprintPilot schema.
    """
    base_url = os.getenv("JIRA_URL")
    if not base_url:
        logger.warning("JIRA_URL not set")
        return []
    
    key = project_key or os.getenv("JIRA_PROJECT_KEY")
    if not key:
        logger.warning("JIRA_PROJECT_KEY not set")
        return []
    
    try:
        # Build JQL query
        jql = f"project={key} AND status != Done ORDER BY created DESC"
        
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.get(
                f"{base_url}/rest/api/3/search",
                headers={
                    "Authorization": _auth_header(),
                    "Accept": "application/json"
                },
                params={
                    "jql": jql,
                    "maxResults": max_results,
                    "fields": "summary,description,labels,status,assignee,priority,customfield_10016,customfield_10004"
                }
            )
            resp.raise_for_status()
            data = resp.json()
        
        issues = data.get("issues", [])
        result = []
        
        for issue in issues:
            fields = issue.get("fields", {})
            
            # Extract description
            desc = fields.get("description")
            if desc:
                if isinstance(desc, str):
                    description = desc
                elif isinstance(desc, dict):
                    # Jira's ADF format - extract plaintext
                    description = desc.get("content", [{}])[0].get("content", [{}])[0].get("text", "No description")
                else:
                    description = "No description"
            else:
                description = "No description"
            
            # Map assignee
            assignee = fields.get("assignee")
            assignee_name = assignee.get("displayName") if assignee else None
            
            mapped = {
                "id": f"JIRA-{issue['key']}",
                "title": fields.get("summary", "Untitled"),
                "description": description,
                "labels": fields.get("labels", []),
                "status": _map_status(fields.get("status", {}).get("name", "To Do")),
                "assignee": assignee_name,
                "story_points": _extract_story_points(fields),
            }
            result.append(mapped)
        
        return result
    
    except httpx.HTTPStatusError as e:
        logger.exception(f"Jira fetch failed: HTTP {e.response.status_code}: {e.response.text[:200]}")
        return []
    except Exception as e:
        logger.exception(f"Error fetching Jira issues: {e}")
        return []


async def fetch_sprint_history(board_id: Optional[int] = None) -> list:
    """
    Pull closed sprint records from a Jira Agile board.
    """
    base_url = os.getenv("JIRA_URL")
    bid = board_id or os.getenv("JIRA_BOARD_ID")
    
    if not base_url:
        logger.warning("JIRA_URL not set")
        return []
    
    if not bid:
        logger.warning("JIRA_BOARD_ID not set")
        return []
    
    try:
        async with httpx.AsyncClient(timeout=30) as client:
            # Get closed sprints
            resp = await client.get(
                f"{base_url}/rest/agile/1.0/board/{bid}/sprint",
                headers={
                    "Authorization": _auth_header(),
                    "Accept": "application/json"
                },
                params={"state": "closed"}
            )
            resp.raise_for_status()
            data = resp.json()
        
        sprints = data.get("values", [])
        result = []
        
        for i, sprint in enumerate(sprints):
            sprint_id = sprint.get("id")
            
            try:
                # Get issues for this sprint
                async with httpx.AsyncClient(timeout=30) as client:
                    issues_resp = await client.get(
                        f"{base_url}/rest/agile/1.0/sprint/{sprint_id}/issue",
                        headers={
                            "Authorization": _auth_header(),
                            "Accept": "application/json"
                        },
                        params={
                            "fields": "status,customfield_10016,customfield_10004,customfield_10003"
                        }
                    )
                    issues_resp.raise_for_status()
                    issues_data = issues_resp.json()
            except Exception as e:
                logger.warning(f"Failed to fetch issues for sprint {sprint_id}: {e}")
                continue
            
            issues = issues_data.get("issues", [])
            total_pts = 0
            done_pts = 0
            
            for issue in issues:
                pts = _extract_story_points(issue.get("fields", {}))
                total_pts += pts
                
                if issue.get("fields", {}).get("status", {}).get("name", "") == "Done":
                    done_pts += pts
            
            mapped = {
                "sprint": i + 1,
                "start": sprint.get("startDate", "")[:10] if sprint.get("startDate") else "",
                "end": sprint.get("endDate", "")[:10] if sprint.get("endDate") else "",
                "committed": total_pts,
                "completed": done_pts,
                "velocity": done_pts,
            }
            result.append(mapped)
        
        return result
    
    except httpx.HTTPStatusError as e:
        logger.exception(f"Jira sprint history fetch failed: HTTP {e.response.status_code}")
        return []
    except Exception as e:
        logger.exception(f"Error fetching Jira sprint history: {e}")
        return []

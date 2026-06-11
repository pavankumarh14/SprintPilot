"""
SprintPilot — GitHub Issues API Client
========================================
Implemented ✅

Pull open issues from a GitHub repository so SprintPilot can use
GitHub Issues as a backlog source instead of seed data.
"""
import os
import logging
import httpx
from typing import Optional

logger = logging.getLogger(__name__)

GITHUB_API_URL = "https://api.github.com"


def _auth_header() -> dict:
    token = os.getenv("GITHUB_TOKEN", "")
    return {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28"
    }


def is_configured() -> bool:
    return all([
        os.getenv("GITHUB_TOKEN"),
        os.getenv("GITHUB_OWNER"),
        os.getenv("GITHUB_REPO"),
    ])


async def fetch_issues(
    owner: Optional[str] = None,
    repo: Optional[str] = None,
    max_results: int = 50,
) -> list:
    """
    Pull open issues from a GitHub repo and return them in SprintPilot schema.
    """
    resolved_owner = owner or os.getenv("GITHUB_OWNER")
    resolved_repo = repo or os.getenv("GITHUB_REPO")
    token = os.getenv("GITHUB_TOKEN")
    
    if not resolved_owner or not resolved_repo or not token:
        logger.warning("GitHub credentials not configured")
        return []
    
    try:
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.get(
                f"{GITHUB_API_URL}/repos/{resolved_owner}/{resolved_repo}/issues",
                headers=_auth_header(),
                params={
                    "state": "open",
                    "per_page": max_results
                }
            )
            resp.raise_for_status()
            issues = resp.json()
        
        result = []
        
        for issue in issues:
            # Filter out pull requests
            if issue.get("pull_request") is not None:
                continue
            
            # Extract labels
            labels = [l["name"] for l in issue.get("labels", [])]
            
            # Extract story points from labels (format: "points:X" or "size:X")
            story_points = 0
            for label in labels:
                if label.lower().startswith("points:") or label.lower().startswith("size:"):
                    try:
                        story_points = int(label.split(":")[1])
                        break
                    except (ValueError, IndexError):
                        pass
                # Also check for label names like "1", "2", "3", "5", "8", "13"
                if label in ["1", "2", "3", "5", "8", "13", "21"]:
                    try:
                        story_points = int(label)
                    except ValueError:
                        pass
            
            assignee = issue.get("assignee")
            assignee_login = assignee["login"] if assignee else None
            
            mapped = {
                "id": f"GH-{issue['number']}",
                "title": issue.get("title", "Untitled"),
                "description": issue.get("body") or "No description",
                "labels": labels,
                "status": "todo",
                "assignee": assignee_login,
                "story_points": story_points,
                "url": issue.get("html_url"),
            }
            result.append(mapped)
        
        return result
    
    except httpx.HTTPStatusError as e:
        logger.exception(f"GitHub fetch failed: HTTP {e.response.status_code}: {e.response.text[:200]}")
        return []
    except Exception as e:
        logger.exception(f"Error fetching GitHub issues: {e}")
        return []

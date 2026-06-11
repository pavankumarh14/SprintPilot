"""
SprintPilot — Sprint Alert Notifier
======================================
Implemented ✅
"""
import os
import logging
import httpx
import re
from typing import Optional

logger = logging.getLogger(__name__)

ALERT_THRESHOLD = 0.70
SENDGRID_SEND_URL = "https://api.sendgrid.com/v3/mail/send"
SENDER_EMAIL = "noreply@sprintsense.ai"


def build_slack_blocks(
    probability: float,
    current_day: int,
    at_risk: list,
) -> dict:
    """
    Build a Slack Block Kit payload for the slippage alert.
    """
    pct = round(probability * 100)
    status = "⚠️ declining" if at_risk else "✅ on-track"
    
    blocks = [
        {
            "type": "header",
            "text": {
                "type": "plain_text",
                "text": f"⚠️ SprintPilot Alert — Day {current_day}",
                "emoji": True
            }
        },
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"*Sprint completion probability: {pct}%*\nStatus: {status} — {len(at_risk)} items at risk"
            }
        },
        {
            "type": "divider"
        }
    ]
    
    # Add at-risk items
    for item in at_risk:
        blocks.append({
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"*[{item.get('risk_level', 'MEDIUM').upper()}]* `{item.get('ticket_id', 'N/A')}` — {item.get('title', 'Untitled')}\n>{item.get('reason', 'No reason provided')}"
            }
        })
    
    if not at_risk:
        blocks.append({
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": "✅ No items currently at risk. Sprint is on track."
            }
        })
    
    return {"blocks": blocks}


async def send_slack_alert(
    probability: float,
    current_day: int,
    at_risk: list,
    webhook_url: Optional[str] = None,
) -> None:
    """
    POST the alert to Slack if probability < ALERT_THRESHOLD.
    """
    # Check if alert is needed
    if probability >= ALERT_THRESHOLD:
        return
    
    # Resolve webhook URL
    url = webhook_url or os.getenv("SLACK_WEBHOOK_URL")
    if not url:
        logger.warning("SLACK_WEBHOOK_URL not set")
        return
    
    try:
        payload = build_slack_blocks(probability, current_day, at_risk)
        
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.post(url, json=payload)
            
            if resp.status_code == 200:
                logger.info(f"Slack alert sent (HTTP {resp.status_code})")
            else:
                logger.warning(f"Slack alert failed: {resp.text}")
    
    except Exception as e:
        logger.exception(f"Error sending Slack alert: {e}")


def markdown_to_html(text: str) -> str:
    """
    Convert the standup digest markdown to minimal HTML for email rendering.
    """
    if not text:
        return "<html><body></body></html>"
    
    html = text
    
    # Bold: **text** -> <strong>text</strong>
    html = re.sub(r'\*\*(.*?)\*\*', r'<strong>\1</strong>', html)
    
    # Italic: *text* -> <em>text</em> (but not **)
    html = re.sub(r'(?<!\*)\*(?!\*)(.*?)\*(?!\*)', r'<em>\1</em>', html)
    
    # Code: `text` -> <code>text</code>
    html = re.sub(r'`([^`]+)`', r'<code>\1</code>', html)
    
    # Headers: # text -> <h2>text</h2>
    html = re.sub(r'^# (.+)$', r'<h2>\1</h2>', html, flags=re.MULTILINE)
    
    # List items: - text -> <li>text</li>
    lines = html.split('\n')
    result_lines = []
    in_list = False
    
    for line in lines:
        stripped = line.lstrip()
        if stripped.startswith('- '):
            if not in_list:
                result_lines.append('<ul>')
                in_list = True
            item_text = stripped[2:]
            result_lines.append(f'<li>{item_text}</li>')
        else:
            if in_list:
                result_lines.append('</ul>')
                in_list = False
            result_lines.append(line)
    
    if in_list:
        result_lines.append('</ul>')
    
    html = '\n'.join(result_lines)
    
    # Paragraph breaks: \n\n -> </p><p>
    html = html.replace('\n\n', '</p><p>')
    
    # Single newlines: \n -> <br/>
    html = html.replace('\n', '<br/>')
    
    # Wrap in HTML wrapper
    html = f"<html><body><p>{html}</p></body></html>"
    
    return html


async def send_email_digest(
    digest_text: str,
    to_email: Optional[str] = None,
    subject: str = "SprintPilot Daily Digest",
    api_key: Optional[str] = None,
) -> None:
    """
    Send the daily standup digest as an HTML email via SendGrid.
    """
    # Resolve API key
    key = api_key or os.getenv("SENDGRID_API_KEY")
    if not key:
        logger.warning("SENDGRID_API_KEY not set")
        return
    
    # Resolve recipient
    recipient = to_email or os.getenv("ALERT_TO_EMAIL", "team@sprintsense.ai")
    
    # Convert markdown to HTML
    html = markdown_to_html(digest_text)
    
    # Build SendGrid payload
    payload = {
        "personalizations": [{"to": [{"email": recipient}]}],
        "from": {"email": SENDER_EMAIL, "name": "SprintPilot"},
        "subject": subject,
        "content": [{"type": "text/html", "value": html}],
    }
    
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.post(
                SENDGRID_SEND_URL,
                headers={"Authorization": f"Bearer {key}"},
                json=payload
            )
            
            if resp.status_code == 202:
                logger.info(f"Email digest sent to {recipient}")
            else:
                logger.warning(f"SendGrid error {resp.status_code}: {resp.text[:120]}")
    
    except Exception as e:
        logger.exception(f"Error sending email digest: {e}")

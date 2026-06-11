from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from app.data.seed_data import SPRINT_BOARD, BACKLOG_TICKETS, LLM_ESTIMATES

router = APIRouter()


class MoveRequest(BaseModel):
    ticket_id: str
    status: str   # "todo" | "in_progress" | "review" | "done"


@router.post("/move")
def move_ticket(body: MoveRequest):
    """
    Move a ticket to a different Kanban column and return the updated board.
    """
    ticket_id = body.ticket_id
    target_status = body.status
    
    # Validate status
    valid_statuses = ["todo", "in_progress", "review", "done"]
    if target_status not in valid_statuses:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid status '{target_status}'. Must be one of: {valid_statuses}"
        )
    
    # Search for ticket in all columns
    found_column = None
    found_ticket = None
    
    for column in valid_statuses:
        if ticket_id in SPRINT_BOARD[column]:
            found_column = column
            found_ticket = ticket_id
            break
    
    # Check if ticket exists in backlog (case-insensitive lookup)
    normalized_id = ticket_id.upper()
    backlog_ticket = None
    for t in BACKLOG_TICKETS:
        if t["id"].upper() == normalized_id:
            backlog_ticket = t
            break
    
    # If not found in board but exists in backlog, add it to the board first
    if not found_column and backlog_ticket:
        # Add to "todo" column
        SPRINT_BOARD["todo"].append(ticket_id)
        found_column = "todo"
        found_ticket = ticket_id
    elif not found_column:
        raise HTTPException(
            status_code=404,
            detail=f"Ticket '{ticket_id}' not found"
        )
    
    # Remove from current column
    if found_ticket in SPRINT_BOARD[found_column]:
        SPRINT_BOARD[found_column].remove(found_ticket)
    
    # Add to target column
    SPRINT_BOARD[target_status].append(ticket_id)
    
    # Update backlog ticket status
    for t in BACKLOG_TICKETS:
        if t["id"].upper() == normalized_id:
            t["status"] = target_status
            break
    
    # Return updated board
    return get_board()


@router.get("/")
def get_board():
    def enrich(ids, column):
        result = []
        for tid in ids:
            t = next((x for x in BACKLOG_TICKETS if x["id"] == tid), {})
            est = LLM_ESTIMATES.get(tid, {})
            result.append({**t, "status": column, "estimate": est})
        return result

    return {
        "todo":        enrich(SPRINT_BOARD["todo"],        "todo"),
        "in_progress": enrich(SPRINT_BOARD["in_progress"], "in_progress"),
        "review":      enrich(SPRINT_BOARD["review"],      "review"),
        "done":        enrich(SPRINT_BOARD["done"],        "done"),
    }

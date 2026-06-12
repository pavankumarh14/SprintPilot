from fastapi import FastAPI, Headerf
rom fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from pathlib import Path
from typing import Optional
from app.api import backlog, sprint, forecast, team, board, integrations, scenarios
from app.services.llm import has_real_key

app = FastAPI(title="SprintPilot API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*", "X-LLM-Key"],
    expose_headers=["*"],
)

app.include_router(backlog.router, prefix="/api/backlog", tags=["backlog"])
app.include_router(sprint.router,  prefix="/api/sprint",  tags=["sprint"])
app.include_router(forecast.router, prefix="/api/forecast", tags=["forecast"])
app.include_router(team.router,    prefix="/api/team",    tags=["team"])
app.include_router(board.router,   prefix="/api/board",        tags=["board"])
app.include_router(integrations.router, prefix="/api/integrations", tags=["integrations"])
app.include_router(scenarios.router, prefix="/api/scenarios", tags=["scenarios"])


@app.get("/api/health")
def health():
    return {"status": "ok", "service": "SprintPilot API"}


@app.get("/api/llm-status")
def llm_status(x_llm_key: Optional[str] = Header(default=None)):
    """
    Returns whether a real LLM key is active (per-request or env-level).
    Frontend polls this after the user saves a key.
    """
    active = has_real_key(x_llm_key)
    return {"llm_active": active, "source": "header" if x_llm_key else ("env" if active else "none")}


# Serve React static files
STATIC_DIR = Path(__file__).parent.parent.parent / "frontend" / "build"

if STATIC_DIR.exists():
        # Mount static assets (JS, CSS, images)
        app.mount("/static", StaticFiles(directory=STATIC_DIR / "static"), name="static")

# Serve index.html for all non-API routes (client-side routing)
@app.get("/{full_path:path}")
async def serve_react_app(full_path: str):
    if full_path.startswith("api/"):
        return {"error": "Not found"}
    
    index_file = STATIC_DIR / "index.html"
    if index_file.exists():
        with open(index_file, "r") as f:
            return HTMLResponse(content=f.read())
    return {"error": "Frontend not built"}

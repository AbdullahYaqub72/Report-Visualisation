"""
main.py — FastAPI Backend for SQL AI Dashboard
Run with: uvicorn main:app --reload --port 8000
"""
import logging
import os
import json
import asyncio
from typing import Any, Dict, List, Optional

import uvicorn
from fastapi import FastAPI, HTTPException, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from agent import run_sql_agent
from analyzer import analyze_data, recommend_charts
from dashboard import generate_dashboard

# ─────────────────────────────────────────────
# Logging
# ─────────────────────────────────────────────
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────
# App
# ─────────────────────────────────────────────
app = FastAPI(
    title="SQL AI Dashboard API",
    description="Natural language → SQL → Data → Visualization",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Serve the frontend (if frontend/ folder exists alongside main.py)
frontend_dir = os.path.join(os.path.dirname(__file__), "..", "frontend")
if os.path.isdir(frontend_dir):
    app.mount("/app", StaticFiles(directory=frontend_dir, html=True), name="frontend")


# ─────────────────────────────────────────────
# Schema
# ─────────────────────────────────────────────
class QueryRequest(BaseModel):
    provider: str = Field(..., description="openai | google | anthropic")
    model_name: str = Field(..., description="e.g. gpt-4o, gemini-2.5-flash, claude-3-5-sonnet-20241022")
    api_key: str = Field(..., description="Provider API key")
    db_url: str = Field(..., description="SQLAlchemy connection URI")
    query: str = Field(..., description="Natural language question")


class ChartRec(BaseModel):
    type: str
    title: str
    description: str
    primary: bool
    reasoning: Optional[str] = None


class QueryResponse(BaseModel):
    sql_query: str
    data: List[Dict[str, Any]]
    columns: List[str]
    row_count: int
    insights: str
    chart_recommendations: List[Dict]
    dashboard_html: str


class ErrorResponse(BaseModel):
    error: str
    detail: Optional[str] = None


# ─────────────────────────────────────────────
# Endpoints
# ─────────────────────────────────────────────
@app.get("/")
async def root():
    return {"message": "SQL AI Dashboard API is running. POST to /api/query"}


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.post("/api/query", response_model=QueryResponse)
async def run_query(request: QueryRequest):
    logger.info(f"Query request: provider={request.provider}, model={request.model_name}")

    # Validate inputs
    if not request.api_key.strip():
        raise HTTPException(status_code=400, detail="API key is required.")
    if not request.db_url.strip():
        raise HTTPException(status_code=400, detail="Database URL is required.")
    if not request.query.strip():
        raise HTTPException(status_code=400, detail="Query is required.")

    try:
        # ── 1. Run SQL Agent ───────────────────────────
        agent_result = await run_sql_agent(
            provider=request.provider,
            model_name=request.model_name,
            api_key=request.api_key,
            db_url=request.db_url,
            query=request.query,
        )

        data = agent_result["data"]
        columns = agent_result["columns"]
        sql_query = agent_result["sql_query"]

        # ── 2. Analyze Data ────────────────────────────
        analysis = analyze_data(data, columns)

        # ── 3. Chart Recommendations ───────────────────
        chart_recs = recommend_charts(analysis)

        # ── 4. Generate Dashboard ──────────────────────
        dashboard_html = generate_dashboard(
            query=request.query,
            sql=sql_query,
            data=data,
            columns=columns,
            analysis=analysis,
            charts=chart_recs,
        )

        logger.info(f"Success: {len(data)} rows, {len(chart_recs)} chart recommendations")

        return QueryResponse(
            sql_query=sql_query,
            data=data,
            columns=columns,
            row_count=len(data),
            insights=analysis["insights"],
            chart_recommendations=chart_recs,
            dashboard_html=dashboard_html,
        )

    except ValueError as ve:
        logger.error(f"Validation error: {ve}")
        raise HTTPException(status_code=400, detail=str(ve))

    except Exception as exc:
        logger.exception(f"Unexpected error: {exc}")
        raise HTTPException(status_code=500, detail=str(exc))


@app.post("/api/dashboard")
async def get_dashboard_file(request: QueryRequest):
    """Same as /api/query but returns the dashboard HTML directly as a file download."""
    result = await run_query(request)
    return Response(
        content=result.dashboard_html,
        media_type="text/html",
        headers={"Content-Disposition": "attachment; filename=dashboard.html"},
    )


# ─────────────────────────────────────────────
# Dev Server
# ─────────────────────────────────────────────
if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)

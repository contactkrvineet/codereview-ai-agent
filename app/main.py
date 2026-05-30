"""
CodeReview Agent — FastAPI web app.

Endpoints:
    GET  /              Serves the frontend HTML
    POST /api/review    Accepts a GitHub/GitLab URL, returns AI review JSON
    GET  /api/health    Liveness probe (returns 200 OK)
"""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from pathlib import Path
from typing import List, Optional

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel, Field

from .agent.agent import CodeReviewAgent, ReviewIssue
from .agent.llm_client import get_client
from .config import (
    AUTHOR_LINKEDIN,
    AUTHOR_NAME,
    AUTHOR_URL,
    BRAND_NAME,
    BRAND_TAGLINE,
    LLM_API_KEY,
    LLM_MODEL,
    LLM_PROVIDER,
    MAX_FILES_PER_REVIEW,
    SOURCE_URL,
)
from .diff_fetcher import DiffFetchError, fetch_diff
from .rate_limit import rate_limiter
from .url_parser import InvalidURLError, parse_url

logging.basicConfig(level=logging.DEBUG, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger(__name__)
# Keep third-party loggers quieter
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("httpcore").setLevel(logging.WARNING)
logging.getLogger("watchfiles").setLevel(logging.WARNING)


# ─── App lifespan (startup checks) ──────────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Validate config on startup; warn but don't crash if LLM key missing in dev."""
    if not LLM_API_KEY:
        log.warning(
            "⚠️  %s_API_KEY not set. Reviews will fail until you set it. "
            "Get a free Gemini key at https://aistudio.google.com/apikey",
            LLM_PROVIDER.upper(),
        )
    else:
        log.info("✓ LLM provider configured: %s (model: %s)", LLM_PROVIDER, LLM_MODEL)
    yield


# ─── App + static + templates ───────────────────────────────────────────
APP_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = APP_DIR.parent

app = FastAPI(title=BRAND_NAME, version="0.1.0", lifespan=lifespan)
app.mount("/static", StaticFiles(directory=PROJECT_ROOT / "static"), name="static")
templates = Jinja2Templates(directory=PROJECT_ROOT / "templates")


# ─── Request / response models ──────────────────────────────────────────
class ReviewRequest(BaseModel):
    url: str = Field(..., min_length=10, max_length=500)


class ReviewIssueOut(BaseModel):
    file: str
    line: int
    severity: str
    category: str
    message: str

    @classmethod
    def from_issue(cls, issue: ReviewIssue) -> "ReviewIssueOut":
        return cls(
            file=issue.file,
            line=issue.line,
            severity=issue.severity,
            category=issue.category,
            message=issue.message,
        )


class ReviewResponse(BaseModel):
    summary: str
    issues: List[ReviewIssueOut]
    files_reviewed: int
    files_skipped: int
    skip_reasons: List[str]
    source_url: str
    platform: str
    ref_type: str


# ─── Routes ─────────────────────────────────────────────────────────────
@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    brand_first, _, brand_rest = BRAND_NAME.partition(" ")
    return templates.TemplateResponse(
        request,
        "index.html",
        {
            "brand_name": BRAND_NAME,
            "brand_first": brand_first,
            "brand_rest": brand_rest,
            "tagline": BRAND_TAGLINE,
            "author_name": AUTHOR_NAME,
            "author_url": AUTHOR_URL,
            "author_linkedin": AUTHOR_LINKEDIN,
            "source_url": SOURCE_URL,
            "llm_provider": LLM_PROVIDER,
            "llm_model": LLM_MODEL,
        },
    )


@app.get("/api/health")
async def health():
    return {"status": "ok", "version": "0.1.0", "llm_configured": bool(LLM_API_KEY)}


@app.post("/api/review", response_model=ReviewResponse)
async def review(payload: ReviewRequest, request: Request):
    client_ip = _get_client_ip(request)

    # 1. Rate limit
    allowed, message = rate_limiter.check(client_ip)
    if not allowed:
        raise HTTPException(status_code=429, detail=message)

    # 2. Parse URL
    try:
        ref = parse_url(payload.url)
    except InvalidURLError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    # 3. Fetch the diff
    try:
        diff_text = await fetch_diff(ref)
    except DiffFetchError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    if not diff_text.strip():
        return ReviewResponse(
            summary="No code changes found in this diff.",
            issues=[],
            files_reviewed=0,
            files_skipped=0,
            skip_reasons=[],
            source_url=payload.url,
            platform=ref.platform,
            ref_type=ref.ref_type,
        )

    # 4. Run the agent
    if not LLM_API_KEY:
        raise HTTPException(
            status_code=503,
            detail="LLM provider not configured. The operator needs to set GEMINI_API_KEY.",
        )

    try:
        client = get_client(LLM_PROVIDER, model=LLM_MODEL)
        agent = CodeReviewAgent(llm=client, max_files_per_run=MAX_FILES_PER_REVIEW)
        result = agent.review(diff_text)
    except Exception as exc:
        log.exception("Agent review failed")
        raise HTTPException(status_code=500, detail=f"Review failed: {exc}")

    return ReviewResponse(
        summary=result.summary(),
        issues=[ReviewIssueOut.from_issue(i) for i in result.issues],
        files_reviewed=result.files_reviewed,
        files_skipped=result.files_skipped,
        skip_reasons=result.skip_reasons,
        source_url=payload.url,
        platform=ref.platform,
        ref_type=ref.ref_type,
    )


def _get_client_ip(request: Request) -> str:
    """Get client IP, respecting common proxy headers (Render/Railway/Cloudflare)."""
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"

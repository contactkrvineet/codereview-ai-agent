"""
Application configuration.

All branding lives here — to rename the product, change BRAND_NAME and you're done.
"""

import os

from dotenv import load_dotenv

load_dotenv()

# ─── Branding ────────────────────────────────────────────────────────────
BRAND_NAME = "CodeReview Agent"
BRAND_TAGLINE = "AI-powered code review for Quality Engineering teams"
AUTHOR_NAME = "Vineet Kumar"
AUTHOR_URL = "https://vineetkr.com"
AUTHOR_LINKEDIN = "https://linkedin.com/in/vineet2311"
SOURCE_URL = "https://www.vineetkr.com/agents.html"

# ─── LLM Provider ───────────────────────────────────────────────────────
# Free providers available in production:
#   - "gemini"  → Google Gemini (free tier ~1500 requests/day)
#   - "groq"    → Groq (free tier, fast inference)
LLM_PROVIDER = os.getenv("LLM_PROVIDER", "gemini")
LLM_MODEL = os.getenv("LLM_MODEL", "gemini-2.5-flash")
LLM_API_KEY = os.getenv("GEMINI_API_KEY") or os.getenv("LLM_API_KEY", "")

# ─── Rate limiting ──────────────────────────────────────────────────────
# Prevents API cost explosions from public deployment.
# Adjust per your tolerance — these are intentionally conservative for a demo.
RATE_LIMIT_PER_HOUR = int(os.getenv("RATE_LIMIT_PER_HOUR", "10"))
RATE_LIMIT_PER_DAY = int(os.getenv("RATE_LIMIT_PER_DAY", "50"))

# ─── Diff size limits ───────────────────────────────────────────────────
# Avoid hammering the LLM with massive diffs that blow context windows
MAX_DIFF_BYTES = int(os.getenv("MAX_DIFF_BYTES", "200000"))  # 200 KB
MAX_FILES_PER_REVIEW = int(os.getenv("MAX_FILES_PER_REVIEW", "20"))

# ─── Optional GitHub token ──────────────────────────────────────────────
# Raises GitHub unauthenticated rate limit (60/hr) to authenticated (5000/hr).
# Use a read-only token for public repos.
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN", "")

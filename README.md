# CodeReview Agent — Hosted Web App

> AI-powered code review for Quality Engineering teams. Paste a GitHub or GitLab URL, get AI-flagged style and convention violations in seconds.

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Deploy to Render](https://render.com/images/deploy-to-render-button.svg)](https://render.com/deploy)

---

## What this is

A hosted web demo of an AI-assisted code review agent that:

1. Accepts a GitHub PR/commit URL or GitLab MR/commit URL (public repos)
2. Fetches the unified diff via the platform's API
3. Sends each changed file to an LLM (Google Gemini by default, free tier)
4. Returns structured review feedback by file, line, severity, and category

Built as an open-source illustration of a pattern adopted in production at regulated banking environments. The agent is generalized for public reuse — the same architecture supports any team's coding standards via the customizable `prompts/qe_standards.md`.

---

## Live demo

[Deploy your own with one click ↗](https://render.com/deploy) using the included `render.yaml`, or run locally (see below).

---

## Phase 1 vs Phase 2

**This is Phase 1.** Public repositories only. No authentication required from users.

**Phase 2 (planned)** will add:
- OAuth via GitHub and GitLab for private repo support
- Caching layer (Redis) to avoid re-reviewing identical diffs
- Per-user quotas instead of per-IP rate limits

---

## Local development

```bash
# 1. Clone
git clone https://github.com/contactkrvineet/codereview-agent
cd codereview-agent

# 2. Install dependencies
pip install -r requirements.txt

# 3. Set environment variables
cp .env.example .env
# Edit .env — at minimum, add your GEMINI_API_KEY
# Get a free key at https://aistudio.google.com/apikey

# 4. Load env and run the app
export $(cat .env | xargs)
uvicorn app.main:app --reload --port 8000

# 5. Open http://localhost:8000
```

---

## Deploy to Render.com (5 minutes)

Render.com has a generous free tier perfect for a portfolio demo (750 hrs/month, auto-HTTPS, custom domains).

### Steps

1. **Push this repo to your GitHub** (public or private — your choice)

2. **Get a free Gemini API key** at https://aistudio.google.com/apikey

3. **Sign up at https://render.com** (free, no credit card needed)

4. **Create a new Blueprint:**
   - Dashboard → **New +** → **Blueprint**
   - Connect your GitHub account
   - Select this repository
   - Render reads `render.yaml` and provisions the service

5. **Add your secret in the Render dashboard:**
   - Click your new service → **Environment**
   - Add: `GEMINI_API_KEY` = `<your key from step 2>`
   - (Optional) Add: `GITHUB_TOKEN` = `<personal access token>` for higher GitHub rate limits

6. **Deploy.** Render builds the Docker image and your app goes live at a URL like `https://codereview-agent.onrender.com`

7. **Add the live URL to your resume, LinkedIn, and portfolio site.**

### Notes on Render's free tier

- Service sleeps after 15 min of inactivity → first request after sleep takes ~30 seconds (cold start)
- For demos: works fine. Visitors will see "Fetching diff..." then "Sending to LLM..." which masks the cold start.
- For production traffic: upgrade to Render's Starter plan ($7/month) for always-on service.

---

## Alternative deployments

The included `Dockerfile` is portable. You can deploy to:

- **Railway.app** — similar to Render, faster cold starts
- **Fly.io** — global edge deployment, more control
- **Google Cloud Run** — pay per request, scales to zero
- **AWS App Runner** — managed container hosting
- **Any VPS** — `docker build` and `docker run`

---

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Frontend (Jinja2 + JS)                    │
│           Pastes URL → calls POST /api/review                │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                  FastAPI app (app/main.py)                  │
│                                                              │
│   1. url_parser.py    → Parse GitHub/GitLab URL              │
│   2. rate_limit.py    → Check IP-based rate limit            │
│   3. diff_fetcher.py  → Fetch diff via platform API          │
│   4. agent/           → Run AI review                        │
│   5. Return JSON                                             │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                Agent (app/agent/)                            │
│                                                              │
│   diff_parser → prompts → llm_client → response parser       │
│                                                              │
│   LLM provider: pluggable (Gemini, Ollama, OpenAI, Claude)   │
└─────────────────────────────────────────────────────────────┘
```

---

## Project structure

```
codereview-agent-web/
├── README.md                          # You are here
├── Dockerfile                         # Production container
├── render.yaml                        # Render Blueprint config
├── requirements.txt                   # Python dependencies
├── .env.example                       # Local dev environment template
├── .gitignore
├── app/
│   ├── main.py                        # FastAPI app + route handlers
│   ├── config.py                      # All branding + config (single source of truth)
│   ├── url_parser.py                  # GitHub/GitLab URL parsing
│   ├── diff_fetcher.py                # Fetches diffs via platform APIs
│   ├── rate_limit.py                  # In-memory rate limiter
│   └── agent/
│       ├── agent.py                   # Core review orchestration
│       ├── diff_parser.py             # Unified diff → structured objects
│       ├── llm_client.py              # Pluggable LLM backend
│       └── prompts.py                 # Prompt construction
├── prompts/
│   ├── system_prompt.md               # Agent persona & rules
│   └── qe_standards.md                # Coding standards (CUSTOMIZE THIS)
├── templates/
│   └── index.html                     # Beautiful frontend (single file, no framework)
└── static/
    └── (empty — CSS lives inline in index.html for single-file deployment)
```

---

## Configuration

All branding and behavior is in `app/config.py`:

| Variable | Default | Purpose |
|---|---|---|
| `BRAND_NAME` | "CodeReview Agent" | Product name shown in UI |
| `BRAND_TAGLINE` | "AI-powered code review..." | Subtitle on landing page |
| `AUTHOR_NAME` | "Vineet Kumar" | Attribution in footer |
| `LLM_PROVIDER` | `gemini` | Which LLM to use (`gemini`/`ollama`/`openai`/`claude`) |
| `LLM_MODEL` | `gemini-2.0-flash` | Specific model |
| `RATE_LIMIT_PER_HOUR` | `10` | Reviews per IP per hour |
| `RATE_LIMIT_PER_DAY` | `50` | Reviews per IP per day |
| `MAX_DIFF_BYTES` | `200000` | Reject diffs larger than 200 KB |
| `MAX_FILES_PER_REVIEW` | `20` | Cap files per review (cost control) |

To customize the coding standards your agent reviews against, edit `prompts/qe_standards.md`.

---

## Limitations & honest caveats

This is an **illustrative demo**, not a production-grade SaaS:

- **Public repos only.** Private repos require OAuth (Phase 2).
- **In-memory rate limiting.** Works for single-instance deployments; need Redis for multi-worker.
- **No caching.** Identical diffs hit the LLM each time.
- **GitHub free tier rate limit (60/hr without token).** Set `GITHUB_TOKEN` to raise to 5000/hr.
- **No telemetry, no observability.** Add Sentry / Datadog / Grafana for production use.
- **No injection defense.** A malicious commit could include "ignore previous instructions" in code comments. Mitigation pattern (delimiter sandboxing) is on the roadmap.

For a production deployment in a regulated environment, additional infrastructure (audit logging, model output validation, human-in-the-loop gates) would wrap this core agent.

---

## License

MIT — see [LICENSE](LICENSE).

---

## Author

Built by **Vineet Kumar** — QE Lead & AI Automation Architect.
[vineetkr.com](https://vineetkr.com) · [LinkedIn](https://linkedin.com/in/vineet2311) · [GitHub](https://github.com/contactkrvineet)

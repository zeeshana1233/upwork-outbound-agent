# 📋 Project Log — Upwork Outbound Sales Agent

> Last updated: 2026-03-04

---

## 🎯 Project Goal

Build an **Upwork Outbound Sales Agent** — a system that automatically finds relevant Upwork job listings, filters them, and sends targeted opportunities to a Discord server so the team can apply fast.

The project is split into **two modules**:

| Module | Status | Description |
|---|---|---|
| **Module 1 — Lead Finder** | 🔨 In Progress | Scrape Upwork, filter jobs, post to Discord |
| **Module 2 — Auto Applicant** | 🔜 Not Started | Automatically apply to jobs found in Module 1 |

Module 1 itself has **two filtering strategies**:

| Strategy | Status | Description |
|---|---|---|
| **Keyword Approach** | ✅ Built, needs polish | Filter by hard-coded topic/tool keywords |
| **AI Approach** | 🔜 Not Started | Use LLM to score job relevance before posting |

---

## 🏗️ What Has Been Built (Current State)

### Architecture Overview

```
main.py
  └── Starts Discord bot  ──►  bot/discord_bot.py
                                    │
                                    ├── Loads keyword list  ──►  bot/job_search_keywords.py
                                    │
                                    ├── Every 5 seconds: run_advanced_job_searches()
                                    │       └── For each keyword → process_single_search()
                                    │               └── scraper.fetch_jobs(query, filters)
                                    │                       ├── scraper/upwork_scraper.py
                                    │                       ├── scraper/job_search.py
                                    │                       └── scraper/graphql_payloads.py
                                    │
                                    ├── Filter: only jobs posted within last 5 min
                                    ├── Filter: deduplicate by job ID (in-memory set)
                                    ├── Store job in PostgreSQL DB
                                    └── Post rich Discord Embed to correct channel
```

### Files and Their Roles

| File | Role |
|---|---|
| `main.py` | Entry point — init DB, run Discord bot |
| `config.py` | All env-var config (tokens, DB URL, API keys, proxies) |
| `bot/discord_bot.py` | Discord bot core — polling loop, message formatting, posting logic |
| `bot/job_search_keywords.py` | The keyword list — queries, categories, Discord channel mapping |
| `scraper/upwork_scraper.py` | `UpworkScraper` class — manages auth tokens, cookies, HTTP session |
| `scraper/job_search.py` | `fetch_jobs()` — builds GraphQL request, applies post-processing filters |
| `scraper/graphql_payloads.py` | GraphQL query strings for Upwork visitor API |
| `scraper/job_details.py` | Fetches full job detail page (client info, budget, requirements) |
| `scraper/cookies.py` | Browser cookie snapshot for API auth |
| `db/models.py` | SQLAlchemy models: `Job`, `BHWThread` |
| `db/database.py` | PostgreSQL engine + `SessionLocal` + `init_db()` |
| `scraper/bhw_scraper.py` | BHW forum scraper (separate feature, currently commented out) |

---

## 🔄 How the Bot Loops

1. Bot starts → `on_ready()` fires → launches `run_scrapers_concurrently()`
2. Every **5 seconds**, all keyword searches run **concurrently** via `asyncio.gather()`
3. Each search:
   - Calls Upwork's **visitor GraphQL API** with the keyword query
   - Post-processes results: filters by `payment_verified=True` and `contractor_tier=[2,3]` (Intermediate/Expert)
   - Checks each job: **posted within last 5 minutes?** → if not, skip
   - Checks each job: **already sent?** (in-memory `sent_job_ids` set) → if yes, skip
   - Stores new job in PostgreSQL to prevent duplicates across restarts
   - Fetches full job details and posts a rich Discord Embed to the appropriate channel

---

## ✅ What's Working

- [x] Upwork visitor GraphQL API integration (no login required)
- [x] Batched concurrent polling — 5 keywords at a time, ~90s per full 25-keyword scan
- [x] Real-time detection (5-minute freshness window)
- [x] Duplicate prevention (in-memory `sent_job_ids` set — marks ALL seen IDs regardless of age)
- [x] Rich Discord Embed messages with job details
- [x] Multiple Discord channels — each keyword category posts to its own channel
- [x] `contractor_tier` filter (Intermediate + Expert only, post-processing)
- [x] BHW forum scraper (built, currently disabled/commented out)
- [x] Deployed as Windows Service (NSSM) on `38.242.198.21` — survives reboots
- [x] GitHub Actions CI/CD — every push to `main` auto-deploys to server in ~10s

---

## ❌ Known Problems

- **Too much noise** — the keyword approach is too broad. Queries like `"bot"`, `"selenium"`, `"zapier"` return many irrelevant jobs
- **No semantic understanding** — a job titled "Instagram bot removal" matches the "bot" keyword even though it's not a lead
- **In-memory dedup resets on restart** — `sent_job_ids` is a Python `set()`, so it resets on bot restart (PostgreSQL dedup is broken on current server — `jobs.job_id` column missing)
- **DB dedup non-functional on Windows server** — `Error saving job to DB: column jobs.job_id does not exist`. Non-blocking but dedup doesn't persist across restarts
- **No logging/alerting on errors** — errors written to `C:\upwork-outbound-agent\logs\error.log` on server but no alerting

---

## 🔜 Next Steps (Planned)

### Phase 1 — Polish Keyword Approach (Current Focus)
- [x] Review and tighten existing keyword queries (removed overly broad ones like `"bot"`, split giant Web Dev query)
- [x] Add negative keywords / exclusion filters for known noise terms (expanded from 2 → 15+ terms)
- [x] Add title-only search for ambiguous terms (all broad terms now use `title:()` scoping)
- [x] Add budget floor filter (skip fixed-price jobs under $200)
- [ ] Tune `contractor_tier` and `payment_verified` filters per category (next)

### Phase 2 — AI Filtering Layer
- [ ] After scraping, pass job title + description to Gemini/GPT
- [ ] Prompt: "Is this job a good lead for [our service]? Score 1-10 and explain"
- [ ] Only post jobs scoring above threshold (e.g. 7/10)
- [ ] Log AI decisions to DB for review and prompt tuning

### Phase 3 — Discord Integration Polish
- [ ] Add `/set_channel` slash command to configure channel routing
- [ ] Add thumbs-up/thumbs-down reactions for manual feedback
- [ ] Surface feedback to improve AI scoring prompts

### Phase 4 — Module 2: Auto Applicant
- [ ] When a job is approved (thumbs up), trigger cover letter generation
- [ ] Auto-submit proposal via Upwork API or Selenium
- [ ] Track proposal status

---

## 🗒️ Session Notes

### 2026-03-02 — Session 1
- Read entire codebase to understand current state
- Created `PROJECT_LOG.md` (this file)
- Created `KEYWORD_APPROACH.md` — detailed explanation of how keyword filtering works
- Identified main problem: keyword queries are too broad → too much noise
- Agreed next action: polish keyword list before adding AI layer

### 2026-03-03–04 — Session 3 (Server migration, bug fixes, CI/CD)

**🧹 Cleanup**
- Stopped and deleted bot from old Contabo server (`173.212.215.140`) — service removed, `/opt/upwork-outbound-agent` deleted

**✅ Fix 1 — Rate limiting (Cloudflare 429s)** (`bot/discord_bot.py`)
- Root cause: all 25 keywords fired concurrently → Cloudflare blocked every request
- Fix: changed to batches of 5 concurrent searches with 3–5s delay between batches
- Added `asyncio.Semaphore(5)` in scraper layer
- Result: scan cycle dropped from ~6 min to ~90s, zero 429s

**✅ Fix 2 — Payment verification gate blocking all jobs** (`bot/discord_bot.py`)
- Root cause: `fetch_job_details` always fails with OAuth2 permission error (visitor API limitation) → all jobs were silently skipped
- Fix: removed hard gate; now posts with basic info if details are unavailable; payment check is a warning only

**✅ Fix 3 — 5-minute time filter (re-added correctly)** (`bot/discord_bot.py`)
- Old bug: jobs marked as seen ONLY if they passed the time filter → same old jobs re-evaluated every cycle
- New logic: ALL job IDs marked seen immediately (prevent re-checking), THEN check `is_job_posted_within_minutes(..., 5)` before posting
- `is_job_posted_within_minutes()` handles ISO 8601 `Z`-suffix strings, Unix timestamps, and datetime objects

**✅ Fix 4 — Speed optimisation** (multiple files)
- Removed `try_minimal_search` fallback — was doubling requests, always failing for empty results
- Reduced pre-search random delay: `0.5–1.5s` (was `2s`)
- Reduced `fetch_job_details` retries: `max_retries=1`, `timeout=10s` (was 3 retries, 45s)
- Reduced scan cycle wait: `60s` (was `180s`)
- Removed verbose per-job JSON dump logging

**✅ Fix 5 — Windows Unicode crash** (server-side NSSM config)
- Root cause: emoji characters in `print()` statements (e.g. `✅`, `⚠️`) crash on Windows CP1252 encoding
- Fix: set `PYTHONIOENCODING=utf-8` + `PYTHONUNBUFFERED=1` in NSSM service environment — no code changes needed

**✅ Fix 6 — `job_details` null safety** (`scraper/job_search.py`)
- `job_details = job_tile.get("job", {}) or {}` — guards against API returning explicit `null` for `job` field

**🚀 Deployment — Windows Desktop Server**
- Server: `38.242.198.21` (Windows, RDP)
- Deployed to `C:\upwork-outbound-agent`
- Installed as Windows Service via NSSM (`C:\nssm-2.24-101-g897c7ad\win64\nssm.exe`)
- Service name: `upwork-outbound-agent`
- Logs: `C:\upwork-outbound-agent\logs\output.log` and `error.log`
- Existing `bhw-bot` (Node.js, Windows Service) left untouched and running
- Both services confirmed `STATE: 4 RUNNING`

**⚙️ CI/CD Pipeline** (`.github/workflows/deploy.yml`)
- Trigger: every push to `main` branch
- Runner: `ubuntu-latest` → SSH into Windows server via `appleboy/ssh-action@v1.2.0`
- Steps: `git reset --hard origin/main` → `pip install` → `sc stop` → `sc start` → `sc query`
- Fixed Windows incompatibility: removed `envs:` / `export` (not supported by cmd.exe)
- Deploy time: ~10–14 seconds
- GitHub Secrets set: `SERVER_HOST`, `SERVER_USER`, `SERVER_PASSWORD`, `ENV_FILE`

**🌿 Branch rename**
- `bhw_bot` → `main` (to avoid confusion with the unrelated `bhw-bot` Node.js project on the server)
- Old `bhw_bot` branch deleted locally and on GitHub
- `main` set as default branch on `zeeshana1233/upwork-outbound-agent`

---

### 2026-03-02 — Session 2 (Phase 1 execution)

**✅ Fix 1 — Tightened broad keyword queries** (`bot/job_search_keywords.py`)
- `"bot"` (single word, extremely noisy) → replaced with title-scoped query covering specific bot types: `title:(bot development) OR title:(automation bot) OR title:(discord bot) OR title:(instagram bot) OR title:(telegram bot) OR title:(twitter bot) OR title:(youtube bot)`
- `"(selenium OR puppeteer OR playwright)"` (matched QA/testing jobs, not builds) → replaced with: `title:(selenium automation) OR title:(puppeteer) OR title:(playwright automation) OR title:(web scraping bot) OR title:(browser automation)`
- Giant Web Dev query (`Flask OR Django OR Mern OR Express OR Electron OR NextJs OR React OR Next OR Laravel OR Frontend OR Website OR development`) → replaced with three focused entries: `React / Next.js Developer`, `Python Web Developer`, `Full Stack Developer` — all using `title:()` scoping

**✅ Fix 2 — Expanded exclusion keyword list** (`scraper/job_search.py`)
- Old list: `['n8n', 'hubspot']` (2 terms)
- New list covers 3 noise categories:
  - **Chatbot noise**: `chatbot`, `chat bot`, `chatgpt bot`, `ai chatbot`, `llm chatbot`, `customer support bot`, `support chatbot`, `conversational ai`
  - **QA/testing noise**: `qa automation`, `test automation`, `unit test`, `e2e test`, `end-to-end test`, `quality assurance`, `manual testing`, `automated testing`
  - **Unrelated tools**: `hubspot`, `salesforce`, `marketo`, `machine learning`, `mlops`, `data pipeline`

**✅ Fix 3 — Added minimum budget floor filter** (`scraper/job_search.py`)
- Jobs with a fixed budget explicitly under **$200** are now skipped
- Hourly jobs without a budget cap always pass through
- Handles string budgets with `$` signs and commas gracefully

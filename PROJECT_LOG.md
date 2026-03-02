# 📋 Project Log — Upwork Outbound Sales Agent

> Last updated: 2026-03-02

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
- [x] Concurrent polling of 20+ keyword searches every 5 seconds
- [x] Real-time detection (5-minute freshness window)
- [x] Duplicate prevention (in-memory set + PostgreSQL)
- [x] Rich Discord Embed messages with job details
- [x] Multiple Discord channels — each keyword category posts to its own channel
- [x] `payment_verified=True` filter
- [x] `contractor_tier` filter (Intermediate + Expert only, post-processing)
- [x] BHW forum scraper (built, currently disabled/commented out)

---

## ❌ Known Problems

- **Too much noise** — the keyword approach is too broad. Queries like `"bot"`, `"selenium"`, `"zapier"` return many irrelevant jobs
- **No semantic understanding** — a job titled "Instagram bot removal" matches the "bot" keyword even though it's not a lead
- **In-memory dedup only survives one session** — `sent_job_ids` is a Python `set()`, so it resets on bot restart (PostgreSQL helps but only for jobs that were stored)
- **Hardcoded auth tokens** — `current_auth_token` and `current_visitor_id` are hardcoded strings in `upwork_scraper.py` and will expire
- **No logging/alerting on errors** — errors are printed to console but not persisted

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

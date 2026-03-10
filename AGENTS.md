# OpenCode Agent — Upwork Outbound Sales Agent

## Project Summary
This bot scrapes Upwork jobs via GraphQL visitor API → filters → posts to Discord → MERIDIAN AI gate scores them → WhatsApp delivers high-signal matches → user replies "agree N" → proposal draft is auto-generated and sent back to WhatsApp.

**Server:** Windows VPS `38.242.198.21`, service name `upwork-outbound-agent`, managed by NSSM  
**Deploy:** GitHub Actions → every push to `main` auto-deploys via SSH in ~12s  
**DB:** PostgreSQL — connection via `POSTGRES_URL` in `.env`

## Module Map
| Module | Status | Entry Point |
|---|---|---|
| Module 1 — Scraper + Discord | ✅ Live | `bot/discord_bot.py` → `run_advanced_job_searches()` |
| Module 2 — MERIDIAN AI Gate | ✅ Live | `meridian/engine.py` → `run_meridian()` |
| Module 3 — Proposal Drafts | ✅ Built | `proposals/generator.py` → `generate_proposal()` |
| Module 4 — Auto Submit | 🔜 Not started | TBD |

## Critical Conventions — Never Break These
- **Never block the Discord posting loop** — MERIDIAN, WhatsApp sends, and proposal generation MUST use `asyncio.create_task()` (fire-and-forget)
- **DB sessions** always use context manager: `with SessionLocal() as s:` — never `session.close()` manually
- **job_id** = Upwork string ID (`~022...`) — strip `~` when building URLs
- **job_number** = sequential integer (1, 2, 3…) — the human-facing ID used in WhatsApp "agree N"
- **Never truncate descriptions before DB** — Discord layer handles display length
- **All new env vars** go in `config.py` first, then `.env.example`
- **Discord channel IDs** are defined only in `bot/job_search_keywords.py` — never hardcode elsewhere
- **Cost tracking** — always call `cost_tracker.record_call(input_tokens, output_tokens)` after every OpenAI call in `meridian/`
- **WhatsApp messages** must stay under 1000 chars — read on mobile
- **Draft HTTP server** runs on `localhost:8765` — WA bridge POSTs here on "agree N"

## Auto-Routing — MANDATORY, Always Active
**You must ALWAYS auto-select the right agent before responding. Never wait for the user to choose.**

Before every reply:
1. Read the task
2. Match it to the table below
3. Adopt that agent's full persona (instructions in `.opencode/agents/`)
4. Start your reply with the mode tag on its own line, e.g. `[scraper-dev]`

| Keywords in task | Agent to become |
|---|---|
| scraper, GraphQL, 401, token, cookies, visitor API, payload, job_search, upwork_scraper | `[scraper-dev]` |
| MERIDIAN, score, threshold, corpus, past_jobs, GPT scoring, prompt, category corpus | `[meridian-tuner]` |
| proposal, draft, agree, cover letter, generate, proposals/ | `[proposal-writer]` |
| DB, model, migration, schema, column, SQLAlchemy, table, alembic | `[db-admin]` |
| deploy, server, NSSM, CI/CD, GitHub Actions, SSH, Windows service, service stop/start | `[deployer]` |
| review, audit, check, any issues, is this correct, smell, anti-pattern | `[code-reviewer]` |
| plan, design, architecture, how should I, what's the best way, module 4 | `[plan]` — analyse only, no file edits |

**If multiple keywords match** → pick the most specific agent (e.g. scraper bug + DB error → `[scraper-dev]`).  
**If nothing matches** → default to `[build]` with full project context.  
**Never ask the user which agent to use.** Always decide and proceed.

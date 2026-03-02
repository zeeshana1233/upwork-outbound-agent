# Upwork Outbound Agent — Lead Finder Bot

> **Module 1 of 2 — complete and running.**  
> Scrapes Upwork in real-time and posts matching job leads to dedicated Discord channels, filtered by keyword, budget, and payment-verification status.

---

## What It Does

1. **Keyword search** — 25 configured searches fire every few minutes across 6 service-specific channels.
2. **Pre-filter** — drops jobs below a $200 budget floor and jobs matching a 15+ term exclusion list (no QA, no chatbots, etc.).
3. **Job detail fetch** — for every candidate job, fetches the full detail page to retrieve the real budget, client history, and payment-verification data.
4. **Payment gate** — discards any job where the client's payment method is not verified. Unverifiable fetches are also dropped.
5. **Discord post** — surviving jobs are posted as rich embeds to the correct channel with budget, skills, client history, and a direct link.
6. **Deduplication** — each job ID is stored in PostgreSQL; a job never appears twice.

---

## Architecture

```
main.py
│
├── bot/
│   ├── discord_bot.py          # Bot loop, per-keyword tasks, embed builder
│   └── job_search_keywords.py  # 25 search configs → channel mapping
│
├── scraper/
│   ├── upwork_scraper.py       # Session management, token extraction, bootstrap
│   ├── job_search.py           # Visitor GraphQL API, semaphore, token-refresh lock
│   ├── job_details.py          # Per-job detail fetch (payment, full budget, skills)
│   ├── graphql_payloads.py     # GraphQL query strings
│   ├── cookies.py              # Cookie helpers
│   ├── db_saver.py             # Dedup + INSERT
│   ├── token_manager.py        # OAuth2 token lifecycle
│   └── bhw_scraper.py          # (reserved)
│
├── db/
│   ├── database.py             # SQLAlchemy engine / session factory
│   └── models.py               # Job ORM model
│
├── cookies/
│   └── README.md               # Cookie setup instructions
│
├── config.py                   # Env-var loader
├── requirements.txt
└── .env.example                # Template — copy to .env
```

---

## Quick Start

```bash
# 1. Clone
git clone git@github.com:zeeshana1233/upwork-outbound-agent.git
cd upwork-outbound-agent

# 2. Install dependencies
pip install -r requirements.txt

# 3. Configure
cp .env.example .env
# Edit .env — add DISCORD_TOKEN and POSTGRES_URL at minimum

# 4. Provision the database
#    Make sure PostgreSQL is running, then the tables are auto-created on first run.

# 5. Run
python main.py
```

---

## Discord Channel Setup

| Channel | Purpose | Keyword categories |
|---|---|---|
| `#appilot` | Android / mobile automation | Android automation, appium, uiautomator |
| `#stealth-mode` | Anti-detect / stealth browsers | Multilogin, GoLogin, AdsPower |
| `#ai-automation` | AI workflow automation | n8n, Make.com, LangChain, GPT agents |
| `#web-dev` | Full-stack web projects | React, Next.js, FastAPI |
| `#tiktok-shop` | TikTok Shop automation | TikTok affiliate, shop automation |
| `#automation` | General automation | Playwright, Puppeteer, Selenium |

Channel IDs are set directly in [bot/job_search_keywords.py](bot/job_search_keywords.py).

---

## Adding / Modifying Keywords

Edit [bot/job_search_keywords.py](bot/job_search_keywords.py). Each entry follows this shape:

```python
{
    "channel_id": 1359407667692572713,    # Discord channel snowflake
    "query": "title:android automation",  # Upwork search query (title: scopes to job title)
    "filters": {
        "budget_min": 200,                # Drop fixed-price jobs below this
        "contractor_tier": ["2", "3"],    # 1=entry, 2=intermediate, 3=expert
    }
}
```

Use `title:` prefix to scope the keyword to the job title only — reduces noise significantly.

---

## Filters Reference

| Filter | Where applied | Effect |
|---|---|---|
| Exclusion keywords | `job_search.py` | 15+ terms — chatbot, testing, QA, Dialogflow, etc. |
| Budget floor (`$200`) | `job_search.py` | Skips fixed-price jobs under $200 |
| `contractor_tier` | GraphQL payload | Only fetches intermediate/expert-tier listings |
| Payment verified | `discord_bot.py` | Drops any job where client payment is not verified |

---

## Environment Variables

See [.env.example](.env.example) for the full list. Minimum required:

| Variable | Required | Description |
|---|---|---|
| `DISCORD_TOKEN` | ✅ | Discord bot token |
| `POSTGRES_URL` | ✅ | PostgreSQL connection string |
| `GEMINI_API_KEY` | Module 2 | Gemini AI scoring (coming soon) |

---

## Requirements

- Python 3.10+
- PostgreSQL 13+
- Discord bot with **Message Content Intent** disabled (the bot only writes, not reads)
- Bot must be invited to the server with `Send Messages` + `Embed Links` permissions

---

## Roadmap

| Module | Status | Description |
|---|---|---|
| Module 1 — Keyword Lead Finder | ✅ **Complete** | Real-time scraping → Discord |
| Module 2 — AI Job Scoring | 🔜 Next | Gemini scores each job 1–10, posts only ≥ 7/10 |
| Module 3 — Auto Proposal Draft | 📋 Planned | GPT drafts a personalised proposal per job |
| Module 4 — CRM Integration | 📋 Planned | Push accepted leads to a CRM / Notion |

---

## Security Notes

- **Never commit `.env`** — it contains your Discord token and DB password. It is blocked by `.gitignore`.
- **Never commit `cookies/*.json`** — also blocked by `.gitignore`.
- Rotate your `DISCORD_TOKEN` if it is ever exposed.

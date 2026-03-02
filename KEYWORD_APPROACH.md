# 🔍 Keyword Approach — How It Works

> This document explains the current keyword-based job filtering system end-to-end.
> Reference date: 2026-03-02

---

## Overview

The keyword approach works like this:

```
Keyword List → GraphQL search query → Upwork API → Post-process filter → Freshness check → Dedup check → Discord
```

Every 5 seconds, the bot runs all defined keyword searches concurrently. Each result goes through a chain of filters before being posted to the correct Discord channel.

---

## Step 1 — The Keyword List

**File:** `bot/job_search_keywords.py`

This is a Python list called `ADVANCED_JOB_SEARCHES`. Each entry is a dictionary describing one search:

```python
{
    "category": "Android Automation",   # Display label (used in logs)
    "keyword":  "Mobile Farm",          # Short display name
    "query":    "Mobile farm",          # Actual Upwork search string
    "channel_id": 1420931314328277012,  # Which Discord channel to post in
    "filters": {
        "payment_verified": True,       # Only show clients who have verified payment
    }
}
```

### Current Categories and Their Keywords

| Category | Keywords |
|---|---|
| **Android Automation** | Mobile Farm, Appium, iPhone Automation, Mobile Bot, Phone Farm, Android Device Automation |
| **Stealth Automation** | Multilogin, GoLogin, Incognition, AdsPower, Browser Fingerprint, Antidetect Browser, Social Media Automation |
| **AI Automation** | n8n, Make.com, Zapier, Pipedream |
| **Web Development** | Web Developer Stack (Flask, Django, MERN, React, Next.js, etc.) |
| **TikTok Shop** | TikTok Shop Manager |
| **Automation (General)** | Bot Development, Browser Automation Tools (Selenium/Puppeteer/Playwright), Browser Automation, Android Accessibility Service |

Each category maps to a **different Discord channel** via `channel_id`.

### Query Syntax

The `query` field is passed directly to Upwork's search engine. Upwork supports some boolean operators:

| Syntax | Meaning | Example |
|---|---|---|
| `word` | Plain keyword anywhere in job | `"Appium"` |
| `title:(word)` | Only match title | `"title:(Mobile bot)"` |
| `description:(word)` | Only match description | `"description:(Multilogin)"` |
| `word AND word` | Both words must appear | `"phone AND farm"` |
| `word OR word` | Either word | `"selenium OR puppeteer OR playwright"` |
| `"exact phrase"` | Exact phrase match | `"browser fingerprint"` |
| `title:(word) OR description:(word)` | In title or description | `"title:(GoLogin) OR description:(GoLogin)"` |

---

## Step 2 — Upwork GraphQL API Call

**File:** `scraper/job_search.py` → `fetch_jobs()`

The bot calls Upwork's **visitor (unauthenticated) GraphQL API**:

```
POST https://www.upwork.com/api/graphql/v1?alias=visitorJobSearch
```

The GraphQL query asks for jobs sorted by **recency** (`"sort": "recency"`), returning up to 100 results per search.

Key request variables:
```json
{
  "sort": "recency",
  "paging": { "offset": 0, "count": 100 },
  "userQuery": "<your query string>"
}
```

The API is called with carefully crafted browser-matching headers and cookies (from `scraper/cookies.py` and `scraper/upwork_scraper.py`) to avoid Cloudflare blocks.

---

## Step 3 — Post-Processing Filters

**File:** `scraper/job_search.py` → `filter_jobs_by_criteria()`

After the API response is received, the bot applies these filters **locally in Python** (because Upwork's visitor API doesn't support all filters server-side):

### 3a. Payment Verified Filter
- Keeps only jobs where `clientPaymentVerificationStatus == "VERIFIED"`
- This means the client has a real payment method on file
- Applied to all searches (hardcoded default)

### 3b. Contractor Tier Filter (Experience Level)
- Keeps only jobs requiring **Intermediate (tier 2)** or **Expert (tier 3)**
- Skips Entry Level (tier 1) jobs
- Applied as default even if not specified in the keyword config

### 3c. Excluded Keywords Filter
- Drops any job whose title, description, or skills contain words from a hardcoded exclusion list
- Current excluded terms: `['n8n', 'hubspot']`

> ⚠️ **Known Issue:** This exclusion list is minimal. It doesn't catch many irrelevant results.

---

## Step 4 — Freshness Check (5-Minute Window)

**File:** `bot/discord_bot.py` → `is_job_posted_within_minutes()`

After filtering, each surviving job is checked:

```python
if not is_job_posted_within_minutes(job.get('createdDateTime'), 5):
    skip  # Job is older than 5 minutes
```

- The `createdDateTime` field from Upwork is parsed (handles ISO string, Unix timestamp, or datetime object)
- Only jobs posted in the **last 5 minutes** are considered
- This keeps the bot focused on new, fresh leads

---

## Step 5 — Deduplication Check

**File:** `bot/discord_bot.py` — `sent_job_ids` set

```python
if job_id in sent_job_ids:
    skip  # Already sent this job in this session
```

Two layers of deduplication:
1. **In-memory set** (`sent_job_ids`) — fast, prevents duplicates within the current bot session
2. **PostgreSQL** (`db/models.py` → `Job` table) — stores `job_id` as a unique key, prevents duplicates across restarts

---

## Step 6 — Fetch Full Job Details

**File:** `bot/discord_bot.py` → `fetch_and_build_job_message()`

Once a job passes all filters, the bot fetches its **full details** from a second API endpoint:

```
POST https://www.upwork.com/api/graphql/v1?alias=gql-query-get-visitor-job-details
```

This returns extra information not in the search results:
- Full description
- Client's total spending history
- Payment verification status (confirmed)
- Engagement duration
- Minimum job success score required
- English proficiency requirement
- Required skills list

---

## Step 7 — Discord Message

**File:** `bot/discord_bot.py` → `build_job_details_embed()`

The bot builds a Discord **Embed** (rich card) with:

| Field | Description |
|---|---|
| Title | Job title, links to Upwork listing |
| Description | First 40 chars of description |
| 💰 Budget | Fixed price or hourly rate |
| 📍 Client Location | Country |
| 💼 Job Type | Fixed / Hourly |
| ⏳ Engagement Duration | Length estimate |
| 💸 Total Spent | Client's historical spend on Upwork |
| ✅ Payment Verified | Yes / No |
| 🏢 Industry | Client's industry |
| ⭐ Min Success Score | Minimum JSS required |
| Footer | Posted X mins ago |

The embed is posted to the **specific Discord channel** mapped to that keyword's `channel_id`.

---

## Complete Flow Diagram

```
                           Every 5 seconds
                                  │
                    ┌─────────────▼──────────────────────────────────────┐
                    │  run_advanced_job_searches()                         │
                    │  asyncio.gather() → all searches run in parallel     │
                    └─────────────┬──────────────────────────────────────-┘
                                  │
                    ┌─────────────▼─────────────┐
                    │  process_single_search()   │  (one per keyword)
                    └─────────────┬─────────────┘
                                  │
                    ┌─────────────▼─────────────┐
                    │  fetch_jobs(query, filters) │
                    │  → Upwork Visitor GraphQL  │
                    └─────────────┬─────────────┘
                                  │
                    ┌─────────────▼──────────────────┐
                    │  filter_jobs_by_criteria()      │
                    │  • payment_verified == True     │
                    │  • contractor_tier in [2, 3]    │
                    │  • not in excluded_keywords     │
                    └─────────────┬──────────────────┘
                                  │
                    ┌─────────────▼──────────────────┐
                    │  is_job_posted_within_minutes() │
                    │  • createdDateTime within 5 min │
                    └─────────────┬──────────────────┘
                                  │
                    ┌─────────────▼──────────────────┐
                    │  Dedup check                    │
                    │  • not in sent_job_ids (memory) │
                    │  • not in PostgreSQL db         │
                    └─────────────┬──────────────────┘
                                  │
                    ┌─────────────▼──────────────────┐
                    │  fetch_and_build_job_message()  │
                    │  → Upwork Job Details API       │
                    └─────────────┬──────────────────┘
                                  │
                    ┌─────────────▼──────────────────┐
                    │  channel.send(embed)            │
                    │  → Correct Discord channel      │
                    └────────────────────────────────┘
```

---

## Why It's Sending Too Many Irrelevant Jobs

The current system over-posts because of these issues:

| Problem | Example | Root Cause |
|---|---|---|
| **Overly broad queries** | `"bot"` matches "Instagram bot removal", "chatbot therapy" | Single-word queries have no semantic constraint |
| **General automation queries** | `"selenium OR puppeteer OR playwright"` catches testing jobs, not automation services | Tools are used in many contexts |
| **`"zapier"` and `"n8n"` as both keywords AND exclusions** | `"zapier"` is searched AND `"n8n"` is excluded — inconsistent | Was added as a keyword, then also blacklisted |
| **Web Dev query is enormous** | Matches any job with `"Flask OR Django OR React OR Next..."` | Too many ORs = too broad |
| **5-minute window filters time, not relevance** | Freshness ≠ relevance | No semantic scoring |

---

## Suggested Improvements (Before Adding AI)

1. **Remove or narrow the broad queries**: `"bot"` → `"title:(bot development)"`, `"selenium OR puppeteer OR playwright"` → `"title:(browser automation)"`
2. **Add exclusion terms to filter out noise**: e.g. exclude `"chatbot"`, `"testing"`, `"QA"`, `"scraping content"` etc.
3. **Add a minimum budget filter**: skip jobs under $200 (most cheap jobs are not good leads)
4. **Remove the Web Dev query or make it much more specific**
5. **Require title match for ambiguous terms**: instead of full-text `"automation"`, use `title:(automation bot)` or `title:(automation script)`

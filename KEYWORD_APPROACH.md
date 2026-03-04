# 🔍 Keyword Approach — How It Works

> This document explains the current keyword-based job filtering system end-to-end.
> Reference date: 2026-03-05 (updated — categories revised from past project history)

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
    "channel_id": 1359407667692572713,  # Which Discord channel to post in
    "filters": {
        "excluded_keywords": ["testing", "qa", "chatbot"],  # Drop irrelevant jobs
    }
}
```

### Categories and Their Keywords

> Categories and keywords are derived from real past project history. Each category has a dedicated Discord channel.

#### 1. Android Automation
**Channel:** `#appilot`  
Jobs involving physical Android devices, phone farms, emulators, ADB scripting, and mobile app interaction at scale.

| Keyword | Query |
|---|---|
| Mobile Farm | `Mobile farm` |
| Appium | `Appium` |
| iPhone Automation | `Iphone Automation` |
| Mobile Bot | `title:(Mobile bot)` |
| Phone Farm | `phone farm` |
| Android Device Automation | `title:(android device automation)` |
| Android Emulator | `title:(android emulator)` |
| ADB Automation | `title:(ADB automation) OR description:(ADB automation)` |
| Emulator Cluster | `title:(emulator cluster) OR description:(emulator cluster)` |
| GPS Emulation | `title:(GPS emulation) OR description:(GPS emulation)` |

**Source projects:** *Android Device Automation for App Interaction at Scale*, *Android Emulator Automation System*, *IG android automation bot*

---

#### 2. Stealth Automation
**Channel:** `#stealth-mode`  
Jobs involving anti-detect browsers, fingerprint spoofing, residential proxies, and multi-account workflows. High-value niche.

| Keyword | Query |
|---|---|
| Multilogin | `title:(Multilogin) OR description:(Multilogin)` |
| GoLogin | `title:(GoLogin) OR description:(GoLogin)` |
| Incognition | `title:(Incognition) OR description:(Incognition)` |
| AdsPower | `title:(AdsPower) OR description:(AdsPower)` |
| Dolphin Anty | `title:(Dolphin Anty) OR description:(Dolphin Anty)` |
| Browser Fingerprint | `title:("browser fingerprint") OR description:("browser fingerprint")` |
| Antidetect Browser | `title:(antidetect) OR description:(antidetect browser)` |
| Residential Proxy | `title:(residential proxy) OR description:(residential proxies)` |
| Fingerprint Spoofing | `title:(fingerprint spoofing) OR description:(fingerprint spoof)` |

**Source projects:** *Multilogin + Selenium Social Media Automation*, *Project Zuckerberg (Facebook + Multilogin)*, *Linkedin Account Automation on GoLogin/Multilogin/Dolphin Anty*, *Incogniton Automation Bot Development*, *Custom bot automation: multilogin and selenium*

---

#### 3. Social Media Automation & SMM
**Channel:** `#smm-bots` *(new channel needed)*  
Jobs for automating social media engagement: buying/scheduling followers, likes, views, retweets via SMM panels. Also includes Twitter/Telegram/Instagram bots for organic-style actions.

| Keyword | Query |
|---|---|
| SMM Panel | `title:(SMM panel) OR description:(SMM panel)` |
| Twitter Bot | `title:(twitter bot)` |
| Instagram Bot | `title:(instagram bot) OR title:(IG bot)` |
| Telegram Bot Automation | `title:(telegram bot) description:(automate)` |
| Follower Automation | `title:(follower) description:(automate)` |
| Engagement Bot | `title:(engagement bot) OR description:(engagement automation)` |
| Social Media Bot | `title:(social media bot)` |
| TikTok Outreach Bot | `title:(tiktok outreach) OR description:(tiktok outreach)` |
| TikTok Comment Bot | `title:(tiktok comment)` |

**Source projects:** *Automate SMM Panel API Purchases for Twitter & Telegram Engagement*, *Twitter bot blocking script*, *IG android automation bot*, *TikTok Comment Reply Bot*, *You will get TikTok Shop Affiliate Mass Outreach Bot* (×9 duplicates — highest demand signal), *New TikTok outreach*

---

#### 4. TikTok Shop
**Channel:** `#tiktok-shop`  
Jobs specifically around TikTok Shop — affiliate programs, manager tools, shop automation.

| Keyword | Query |
|---|---|
| TikTok Shop Manager | `(TikTok AND Shop AND Manager)` |
| TikTok Shop Affiliate | `title:(tiktok shop affiliate)` |
| TikTok Affiliate Outreach | `description:(tiktok) description:(affiliate) description:(outreach)` |
| TikTok Shop Automation | `title:(tiktok shop) description:(automate)` |

**Source projects:** *You will get TikTok Shop Affiliate Mass Outreach Bot*, *TikTok Cloud Project*

---

#### 5. AI Chatbot & LLM Development
**Channel:** `#ai-automation` *(renamed from "AI Automation")*  
Jobs for building AI-powered chatbots, LLM integrations, RAG systems, and document Q&A tools. Also includes no-code workflow tools (n8n, Zapier, Make.com).

| Keyword | Query |
|---|---|
| OpenAI Integration | `title:(openai) OR title:(chatgpt)` |
| LangChain | `title:(langchain) OR description:(langchain)` |
| RAG System | `title:(RAG) OR description:(retrieval augmented)` |
| AI Chatbot | `title:(AI chatbot) OR title:(chatbot AI)` |
| WhatsApp Chatbot | `title:(whatsapp bot) OR title:(whatsapp chatbot)` |
| LLM Developer | `title:(LLM developer) OR description:(large language model)` |
| HuggingFace | `title:(huggingface) OR description:(huggingface)` |
| Vector Database | `title:(vector database) OR description:(vector database)` |
| GPT Developer | `title:(GPT developer) OR title:(GPT-4 developer)` |
| AI Agent | `title:(AI agent) OR description:(AI agent)` |
| n8n | `n8n` |
| Make.com | `make.com` |
| Zapier | `zapier` |
| Pipedream | `pipedream` |

**Source projects:** *AppSeed AI/ML Query Tool (OpenAI, LangChain, HuggingFace)*, *Chatbot AI (WhatsApp + website)*, *Developer - Automated Content Creation with ChatGPT4*, *ChatGPT OpenAI Developer (legal contracts)*, *Create a chatbot on company website (GPT-4, fine-tuning)*, *Developer to create a GPT chatbot off a dataset*, *Build a chat bot*, *GPT Mobile App*

---

#### 6. Web Development
**Channel:** `#web-dev`  
Full-stack and backend web development jobs. Django, React, Node.js, MERN stack.

| Keyword | Query |
|---|---|
| React / Next.js Developer | `title:(React developer) OR title:(Next.js developer) OR title:(NextJS developer)` |
| Python Web Developer | `title:(Django developer) OR title:(Flask developer) OR title:(Python web developer)` |
| Full Stack Developer | `title:(full stack developer) OR title:(MERN developer) OR title:(fullstack developer)` |
| Node.js Developer | `title:(Node.js developer) OR title:(NodeJS developer)` |
| FastAPI Developer | `title:(FastAPI) OR description:(FastAPI developer)` |

**Source projects:** *Full-Stack Django Developer with CI/CD*, *AppSeed AI/ML (Django UI)*, *Node.js & Python Expert Full stack Developer*

---

#### 7. General Automation
**Channel:** `#automation`  
Catch-all for browser automation, bot scripting, and accessibility-based automation not covered by the above categories.

| Keyword | Query |
|---|---|
| Bot Development | `title:(bot development) OR title:(automation bot) OR title:(discord bot) OR title:(telegram bot)` |
| Browser Automation | `browser automation` |
| Browser Automation Tools | `title:(selenium automation) OR title:(puppeteer) OR title:(playwright automation)` |
| Android Accessibility Service | `Android Accessibility Service` |
| Script Automation | `title:(automation script) OR title:(python automation)` |

Each category maps to a **different Discord channel** via `channel_id`.

### Query Syntax

The `query` string is passed as the `userQuery` variable inside the GraphQL request body. **Upwork's own search backend processes it** — we send it as-is, and their server interprets the syntax before returning results. We do not parse it at our level.

**Verified by live test (2026-03-05):**

| Test | Result | Conclusion |
|---|---|---|
| `title:(Multilogin)` → 0 results vs `Multilogin` → 4 results | Different counts | `title:()` **WORKS** server-side |
| `title:(xyz_totally_fake_999)` → 0 results | Returns 0 | `title:()` syntax is processed, not ignored |
| `python AND automation` → 10 vs `python automation` → 10 | Same count | `AND` operator is **IGNORED** (Upwork treats multiple words as AND by default) |
| `title:(Multilogin) OR description:(Multilogin)` → 4 vs each alone → 0 | Union result | `OR` **WORKS** — genuinely unions both field results server-side |
| `title:(selenium) OR title:(puppeteer) OR title:(playwright)` → 10 | Works | Multi-value OR across title fields works |

**What this means for our queries:**

| Syntax | Works? | Notes |
|---|---|---|
| `title:(word)` | ✅ Yes — server-side | Upwork filters to title matches before returning results |
| `description:(word)` | ✅ Yes — server-side | Same field-scoping mechanism as title: |
| `word OR word` | ✅ Yes — server-side | Confirmed: union of results from both sides |
| `title:() OR description:()` | ✅ Yes — server-side | Correct way to catch a term in either field |
| `word AND word` | ❌ Ignored | Default multi-word search is already AND-like; `AND` keyword adds nothing |
| `"exact phrase"` | ✅ Likely yes | Standard search engine behaviour |

**Recommendation:** Use `title:()` and `description:()` with `OR` between them — all confirmed to work server-side. Drop `AND` keywords from all queries since they do nothing. Internal filtering (excluded keywords, budget floor) handles the rest.

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

After the API response is received, the bot applies these filters **locally in Python**:

### ~~3a. Payment Verified Filter~~ — REMOVED
> ❌ `clientPaymentVerificationStatus` is **OAuth2-gated**. The visitor token API returns `ExecutionAborted` when attempting to access this field. Always returned `None`. Removed from all code and config.

### ~~3b. Contractor Tier Filter~~ — REMOVED
> ❌ Contractor tier (experience level) is **not returned** by the visitor search API for post-processing. The filter was silently doing nothing useful since the field is not present in search results. Removed from all code and config.

### 3c. Excluded Keywords Filter ✅ (active)
- Drops any job whose title, description, or skills contain words from a hardcoded exclusion list
- Current excluded terms: `['n8n', 'hubspot', 'testing', 'qa automation', 'chatbot therapy']`
- This is the **only active post-processing filter**

> Each keyword entry in `job_search_keywords.py` can define its own `excluded_keywords` list in `filters`. This allows per-category exclusions (e.g. the Android Automation channel can exclude "gaming" and "AR" while keeping them for other channels).

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
- Engagement duration
- Required skills list

> ⚠️ **Note:** The `jobPubDetails` endpoint returns `ExecutionAborted` for visitor tokens. Fields like client spending, payment verification, client location, JSS requirement, and English requirement are **all OAuth2-gated and unavailable** without a logged-in account.

---

## Step 7 — Discord Message

**File:** `bot/discord_bot.py` → `build_job_details_embed()`

The bot builds a Discord **Embed** (rich card) with:

| Field | Description |
|---|---|
| Title | Job title, links to Upwork listing |
| Description | First 800 chars of description |
| 💰 Budget | Fixed price or hourly rate |
| 💼 Job Type | Fixed / Hourly |
| ⏳ Engagement Duration | Length estimate |
| 🛠 Skills | Up to 15 skill tags |
| Footer | Posted X mins ago |

> **Removed fields** (all require OAuth2 / `jobPubDetails` which is blocked for visitor tokens):
> ~~📍 Client Location~~, ~~💸 Total Spent~~, ~~✅ Payment Verified~~, ~~🏢 Industry~~

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
| **Exclusion list is too short** | Only `['n8n', 'hubspot']` are excluded | Needs to grow with new categories |
| **Web Dev query is broad** | Matches any job with `"Flask OR Django OR React OR Next..."` | Too many ORs = too broad |
| **5-minute window filters time, not relevance** | Freshness ≠ relevance | No semantic scoring |

---

## Roadmap: What Comes After This Document (Steps 2–4)

This document covers **Step 1 (category + keyword design)**. The next steps are:

| Step | What | Status |
|---|---|---|
| **Step 2** | Implement new categories into `job_search_keywords.py` — add new Discord channel for SMM (`#smm-bots`); remove `payment_verified` and `contractor_tier` from all filter dicts | ✅ Done (2026-03-05) |
| **Step 3** | Expand the `excluded_keywords` exclusion list per-category | 🔜 Next |
| **Step 4** | Category classification module — use `title + description + skills` to confirm/reclassify jobs that slip through wrong channels | 🔜 Future |

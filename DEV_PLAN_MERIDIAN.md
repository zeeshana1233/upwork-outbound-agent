# MERIDIAN — Dev Plan v3
### **M**atching **E**ngine for **R**elevance, **I**ntelligence, and **D**omain-**A**ligned **I**ncoming **N**otifications

> Every incoming job gets held at the gate. Only the ones that echo your past wins get through — and you hear about them on WhatsApp.

---

## 1. What Is MERIDIAN?

MERIDIAN is an AI-powered pre-posting gate that intercepts every incoming Upwork job after the existing Discord pipeline runs. It compares each job against a **category-partitioned reference corpus** of your past work, scores it using **GPT (OpenAI)**, and if the score meets the threshold, sends a clean notification to a WhatsApp group. The Discord pipeline is **completely untouched** — jobs continue posting there as before. WhatsApp is a second, filtered, high-signal channel.

### Architecture in One Line
> Discord = everything that passes the existing filter → WhatsApp = only what MERIDIAN approves

---

## 2. Where MERIDIAN Fits in the Existing Pipeline

```
Upwork GraphQL API
        │
        ▼
  fetch_jobs()                ← keyword + category filter (unchanged)
        │
        ▼
filter_jobs_by_criteria()     ← keyword exclusions + budget floor (unchanged)
        │
        ▼
is_job_posted_within_minutes()← only jobs < 5 min old (unchanged)
        │
        ▼
store_job_in_db()             ← DB save (unchanged)
        │
        ▼
channel.send()  ──────────────────────────────► #discord  ← UNCHANGED
        │
        ▼
  ┌─────────────┐
  │  MERIDIAN   │  ◄─── NEW STEP
  │  GATE       │       Category-matched corpus + GPT score
  └─────┬───────┘
        │ score ≥ threshold
        ▼
whatsapp_send()  ─────────────────────────────► WhatsApp Group
```

---

## 3. Delivery Layer — WhatsApp via Baileys

### 3.1 Why Baileys
Baileys is the most mature unofficial WhatsApp Web library (Node.js). It connects via QR scan, maintains a persistent session, and requires no phone number API approval. Zero subscription cost.

### 3.2 Architecture

```
Python (main bot)
       │  HTTP POST  localhost:3001/send
       ▼
┌──────────────────────┐
│  WhatsApp Bridge     │  ← Node.js micro-service  (whatsapp_bridge/)
│  server.js + Baileys │
└──────────────────────┘
       │
       ▼
   WhatsApp Group
```

A **thin Node.js HTTP server** wraps Baileys. The Python bot calls it via `httpx`. On first run the bridge prints a QR code in the terminal — scan once, session is saved to disk and never expires unless you log out.

### 3.3 New Files

```
whatsapp_bridge/
  package.json        ← dependencies: @whiskeysockets/baileys, express, qrcode-terminal
  server.js           ← Express POST /send handler + Baileys QR session
  session/            ← Baileys auth state (gitignored)
  .gitignore
```

### 3.4 Baileys Setup Steps (Phase 1)

```bash
cd whatsapp_bridge
npm init -y
npm install @whiskeysockets/baileys express qrcode-terminal
node server.js        # Scan QR in terminal → session saved to session/
```

`server.js` exposes one endpoint:
```
POST /send
Content-Type: application/json
Body: { "group_jid": "120363...", "message": "..." }
```

### 3.5 Python Side — `meridian/whatsapp.py`

```python
import httpx
import config

async def send_whatsapp(group_jid: str, message: str):
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            await client.post(
                config.WA_BRIDGE_URL,
                json={"group_jid": group_jid, "message": message}
            )
    except Exception as e:
        print(f"[MERIDIAN] WhatsApp send failed: {e}")
```

`group_jid` is the WhatsApp group's internal ID (printed by the bridge on first message to that group). Stored in `.env` as `WA_GROUP_JID`.

### 3.6 New `.env` Variables for WhatsApp

```
WA_BRIDGE_URL=http://localhost:3001/send
WA_GROUP_JID=<your-group-jid>        # printed by bridge once session is live
MERIDIAN_ENABLED=1
MERIDIAN_THRESHOLD=60
PKR_PER_USD=280
OPENAI_API_KEY=sk-...
OPENAI_MODEL=gpt-4o-mini
```

---

## 4. API Cost Tracking — Per-Cycle Finance Report in PKR

### 4.1 Decision: Per-Cycle Finance Report

Every full scan cycle (~2–3 minutes) ends with one WhatsApp finance message. One message per cycle, always present, zero noise. Each individual **job notification also includes that job's own GPT call cost in PKR** — so you always see both per-job spend and cycle total.

**Sample message:**
```
💰 MERIDIAN Finance Report
Cycle: 14:32 UTC | Jobs scored: 47

GPT calls: 47
Input tokens: 96,400 | Output tokens: 4,700
Cost: $0.0158 → ₨ 4.42 PKR

📊 Session total: ₨ 34.82 PKR
```

### 4.2 Cost Calculation

| Model              | Input (per 1M tokens) | Output (per 1M tokens) |
|--------------------|-----------------------|------------------------|
| gpt-4o-mini        | $0.150                | $0.600                 |
| gpt-4o             | $2.50                 | $10.00                 |

**Default: `gpt-4o-mini`** — scores all jobs. Switch to `gpt-4o` via `OPENAI_MODEL` env var for higher accuracy on ambiguous jobs.

PKR conversion uses `PKR_PER_USD` from `.env` (default: 280). Updated manually when needed.

### 4.3 New Table: `meridian_cost_log`

| Column              | Type     | Notes                               |
|---------------------|----------|-------------------------------------|
| `id`                | Integer  | PK auto-increment                   |
| `cycle_at`          | DateTime | UTC timestamp of scan cycle         |
| `jobs_scored`       | Integer  | Number of jobs GPT scored           |
| `input_tokens`      | Integer  | Total prompt tokens this cycle      |
| `output_tokens`     | Integer  | Total completion tokens this cycle  |
| `cost_usd`          | Float    | Calculated USD cost                 |
| `cost_pkr`          | Float    | Calculated PKR cost                 |
| `session_total_pkr` | Float    | Running total since bot start       |

### 4.4 New File: `meridian/cost_tracker.py`

- `record_call(input_tokens, output_tokens)` — accumulates counts for the current cycle
- `flush_cycle_report(jobs_scored) → str` — builds WhatsApp message, saves row to DB, resets counters, returns formatted string
- `get_session_total_pkr() → float` — sums `cost_pkr` from `meridian_cost_log` table

---

## 5. Category-Partitioned Reference Corpus

### 5.1 The Core Insight

Instead of sending **all** past jobs to every GPT call, each incoming job is compared only against past jobs that share its **category**. This keeps the prompt short, improves scoring accuracy, and cuts token cost significantly.

The category comes directly from `search["category"]` — already set on every search entry in `job_search_keywords.py`. No new field needed.

### 5.2 Category Map

| Category Key  | Discord Channel | Keywords Covered                                           |
|---------------|-----------------|------------------------------------------------------------|
| `android`     | #appilot        | Mobile Farm, Appium, iPhone Auto, ADB, Emulator Cluster     |
| `browser`     | #stealth-mode   | Multilogin, GoLogin, Selenium, browser profiles, Dolphin    |
| `social`      | #smm-bots       | Instagram, TikTok, Twitter, LinkedIn bots, SMM panel        |
| `tiktok_shop` | #tiktok-shop    | TikTok Shop outreach, creator invites, affiliate outreach   |
| `ai`          | #ai-automation  | AI agents, LLM, RAG, n8n, workflow automation               |
| `web`         | #web-dev        | Django, React, Next.js, REST APIs, full-stack builds        |
| `automation`  | #automation     | General automation, scrapers, data pipelines                |

### 5.3 How Category Routing Works in the Engine

```python
# meridian/engine.py

CATEGORY_CORPUS_CACHE: dict = {}  # {category: (summary_str, expires_timestamp)}
CACHE_TTL_SECONDS = 1800  # 30 minutes

def build_category_summary(session, category: str) -> str:
    jobs = session.query(PastJob).filter_by(category=category).order_by(
        PastJob.weight.desc()
    ).all()
    # Format as numbered reference entries (see §7.2 for format)
    ...

def get_category_summary(category: str) -> str:
    cached = CATEGORY_CORPUS_CACHE.get(category)
    if not cached or time.time() > cached[1]:
        with SessionLocal() as s:
            summary = build_category_summary(s, category)
        CATEGORY_CORPUS_CACHE[category] = (summary, time.time() + CACHE_TTL_SECONDS)
    return CATEGORY_CORPUS_CACHE[category][0]
```

---

## 6. New Database Schema

### 6.1 New Table: `past_jobs`

| Column             | Type     | Notes                                                           |
|--------------------|----------|-----------------------------------------------------------------|
| `id`               | Integer  | PK auto-increment                                               |
| `title`            | String   | Job title (required)                                            |
| `description`      | Text     | What the client needed / what was built                         |
| `category`         | String   | `android`, `browser`, `social`, `tiktok_shop`, `ai`, `web`, `automation` |
| `skills`           | Text     | JSON list e.g. `["Python","Appium","ADB"]`                      |
| `budget`           | Float    | Numeric budget (NULL if unknown)                                |
| `job_type`         | String   | `hourly` or `fixed` (NULL if unknown)                           |
| `experience_level` | String   | `entry`, `intermediate`, `expert`                               |
| `outcome`          | String   | `won`, `completed`, `passed`, `lost`, `interested`              |
| `weight`           | Float    | Default `1.0`. Higher = more influential in summary.            |
| `source`           | String   | `manual`, `csv_import`, `upwork_db`                             |
| `reference_url`    | String   | Upwork job URL if available                                     |
| `created_at`       | DateTime | Auto UTC                                                        |

### 6.2 New Table: `meridian_cost_log`
Defined in §4.3 above.

### 6.3 Additions to Existing `jobs` Table

| New Column            | Type     | Notes                               |
|-----------------------|----------|-------------------------------------|
| `meridian_score`      | Integer  | 0–100 (NULL = not yet processed)    |
| `meridian_verdict`    | String   | `pass` or `skip`                    |
| `meridian_reasoning`  | Text     | GPT one-paragraph explanation       |
| `meridian_run_at`     | DateTime | Timestamp when MERIDIAN ran         |

---

## 7. MERIDIAN Parameters, Prompt & Scoring

### 7.1 Parameters Sent to the Prompt

These four fields go directly into the GPT prompt for every incoming job:

| Parameter     | Source                   | Why It Matters              |
|---------------|--------------------------|-----------------------------||
| `title`       | `job.get('title')`       | Fastest domain signal       |
| `description` | `job.get('description')` | Core requirement context    |
| `skills`      | `job.get('skills')`      | Direct tech stack signal    |
| `budget`      | `job.get('budget')`      | Viability vs past ranges    |

**`category`** is used only for routing (selecting which past_jobs subset to load). It does **not** appear in the prompt body — the prompt stays compact and model-agnostic.

### 7.2 Compact Category Reference Format (injected into prompt)

```
== PAST WORK REFERENCE: android ==
Reference jobs we have built in this category:

1. "Android Device Automation for App Interaction at Scale"
   Skills: Python, ADB, Android Emulator, Appium, Threading
   Budget: unknown  |  Outcome: completed

2. "Android Emulator Automation System for Google Search & Maps Navigation"
   Skills: Python, ADB, GPS Emulation, Android SDK, Multiprocessing
   Budget: unknown  |  Outcome: won

Key patterns we excel at: device orchestration, emulator clusters, ADB scripting,
parallel device control, session persistence on physical/virtual Android.
```

Generated from `past_jobs` table per category, cached 30 minutes in memory.

### 7.3 Scoring Dimensions — 4 Dimensions, 100 Points

> **Rationale:** Title and Description carry the most signal on Upwork — clients often list vague or incorrect skills. Domain fit and scope clarity are primary. Tech stack is de-weighted (20) because Upwork skill tags are unreliable and often missing.

| Dimension            | Points  | Question Asked                                                      |
|----------------------|:-------:|---------------------------------------------------------------------|
| **Domain Fit**       | 40      | Is this in the specific domain our reference work covers?           |
| **Scope Clarity**    | 25      | Is the requirement specific enough to bid on confidently?           |
| **Tech Stack Match** | 20      | Do the required skills overlap with what we have built before?      |
| **Budget Viability** | 15      | Is the budget realistic against our past project budgets?           |
| **Total**            | **100** |                                                                     |

### 7.4 The GPT Prompt

```
You are a job relevance filter for a freelancer.

{category_reference_summary}

== INCOMING JOB ==
Title: {title}
Description: {description}
Required Skills: {skills}
Budget: {budget}

== TASK ==
Score this incoming job across exactly four dimensions.
Use the reference work above as your strict benchmark.
The job title and description are the most important signals; skill tags on Upwork are often
inaccurate or incomplete — do not over-weight them.

1. Domain Fit (0-40): Does this job fall into the same domain as our reference work?
   Score 0 if clearly outside our specialty (e.g., content creation, QA testing, data science).
   A strong domain match in title and description can score 35-40 even if skills differ.

2. Scope Clarity (0-25): How clearly defined is the client's requirement?
   Vague one-liner = 0-5. Detailed spec with deliverables = 18-25.

3. Tech Stack Match (0-20): How well do the required skills overlap with skills in
   our past reference work? Score based on conceptual overlap — not just exact keyword matches.
   Missing or vague skill list = neutral score of 10.

4. Budget Viability (0-15): Is the stated budget realistic for this type of work?
   Unknown/missing budget = 8 (neutral). Too low = 0-3. Appropriate = 12-15.

== OUTPUT FORMAT ==
Return exactly this JSON. No markdown, no extra text, no explanation outside the JSON.
{
  "domain_fit": <0-40>,
  "scope_clarity": <0-25>,
  "tech_stack_match": <0-20>,
  "budget_viability": <0-15>,
  "total_score": <0-100>,
  "verdict": "<pass|skip>",
  "reasoning": "<one paragraph, max 50 words>"
}

Verdict rule: pass if total_score >= 60, otherwise skip.
```

---

## 8. WhatsApp Message Formats

### 8.1 Job Notification (on pass)

```
🎯 *MERIDIAN MATCH* — Score: 78/100

*Title:* Android Emulator Cluster for App Warming
*Budget:* $1,500 (Fixed)
*Category:* Android Automation
*Skills:* Python • ADB • Appium • Android SDK

*Why it matched:*
Strong domain match — Android emulator cluster work is a direct fit.
Clear deliverable: 30-device cluster. Budget aligns with previous wins.

🔗 https://www.upwork.com/freelance-jobs/apply/~022...

─────────────────────────────
Domain: 36/40 | Clarity: 20/25 | Tech: 14/20 | Budget: 8/15
💰 This job: ₨ 0.09 PKR
```

### 8.2 Per-Cycle Finance Report

```
💰 *MERIDIAN Finance Report*
🕐 Cycle: 14:32 UTC | Jobs scored: 47

GPT calls: 47
Input tokens: 96,400 | Output tokens: 4,700
Cost: $0.0158 → ₨ 4.42 PKR

📊 Session total: ₨ 34.82 PKR
```

---

## 9. New Files and Folder Structure

```
meridian/
  __init__.py
  engine.py             ← build_category_summary(), get_category_summary(), run_meridian(), parse_gpt_response()
  prompt.py             ← MERIDIAN_PROMPT_TEMPLATE constant
  whatsapp.py           ← send_whatsapp(), build_wa_job_message(job, result, category, cost_pkr)
  cost_tracker.py       ← record_call(), flush_cycle_report(), get_session_total_pkr(), get_last_call_cost_pkr()
  seeder.py             ← Load past_jobs.yaml into DB; --from-csv flag for CSV re-import
  data/
    past_jobs.yaml      ← 22-entry corpus seeded from bitbash_projects_cleaned.csv

whatsapp_bridge/
  package.json          ← @whiskeysockets/baileys, express, qrcode-terminal
  server.js             ← Express + Baileys QR auth + POST /send endpoint
  session/              ← Baileys auth state (gitignored)
  .gitignore
```

---

## 10. Seed Data — `meridian/data/past_jobs.yaml`

Built from `bitbash_projects_cleaned.csv` (61 rows, 22 with usable real descriptions).
Private-description jobs excluded. Fields use only information verifiable from the CSV.

```yaml
# ─── ANDROID ─────────────────────────────────────────────────────────────────
- title: "Android Device Automation for App Interaction at Scale"
  description: "Build a cluster of mobile devices/emulators running dozens (eventually hundreds) of Android devices simultaneously. Automate mobile app workflows across all devices in parallel."
  category: android
  skills: ["Python", "Android SDK", "ADB", "Appium", "Threading", "Emulator Management"]
  budget: null
  job_type: fixed
  experience_level: expert
  outcome: completed
  weight: 2.0
  source: csv_import

- title: "Android Emulator Automation System for Google Search & Maps Navigation"
  description: "Develop a scalable software platform managing and orchestrating 30+ Android emulators. Full GPS emulation, Google Maps navigation automation, parallel device control."
  category: android
  skills: ["Python", "ADB", "Android Emulator", "GPS Emulation", "Multiprocessing", "Android SDK"]
  budget: null
  job_type: fixed
  experience_level: expert
  outcome: won
  weight: 2.0
  source: csv_import

# ─── BROWSER AUTOMATION ──────────────────────────────────────────────────────
- title: "Incogniton Automation Bot Development"
  description: "Build automation bot for Multilogin environment. Facebook automation across multiple browser profiles."
  category: browser
  skills: ["Python", "Selenium", "Multilogin", "Browser Automation", "Facebook Automation"]
  budget: null
  job_type: fixed
  experience_level: intermediate
  outcome: completed
  weight: 1.5
  source: csv_import

- title: "Custom Bot Automation — Multilogin and Selenium"
  description: "Script a customized desktop and browser bot using Multilogin and Selenium for multi-account automation."
  category: browser
  skills: ["Python", "Selenium", "Multilogin", "Browser Automation"]
  budget: null
  job_type: fixed
  experience_level: intermediate
  outcome: completed
  weight: 1.0
  source: csv_import

- title: "Multilogin + Selenium Social Media Automation"
  description: "Automate social media interactions to emulate human behaviour. Multi-account management with MLA (Multilogin) and Selenium. Separate sessions with human-like timing."
  category: browser
  skills: ["Selenium", "Multilogin", "Python", "Social Media Automation", "Browser Profiles"]
  budget: null
  job_type: fixed
  experience_level: expert
  outcome: completed
  weight: 1.5
  source: csv_import

- title: "LinkedIn Account Automation on GoLogin / Multilogin / Dolphin Anty"
  description: "Build scalable LinkedIn automation managing multiple accounts using GoLogin/Multilogin/Dolphin Anty. Automate messaging, connection requests, and profile actions."
  category: browser
  skills: ["Python", "GoLogin", "Multilogin", "Dolphin Anty", "Selenium", "LinkedIn Automation"]
  budget: null
  job_type: fixed
  experience_level: expert
  outcome: won
  weight: 2.0
  source: csv_import

- title: "Long Term Support and Updates for Selenium Bot"
  description: "Maintain, update, and improve an existing Selenium automation bot. Ongoing hourly support contract."
  category: browser
  skills: ["Python", "Selenium", "Bot Maintenance", "Browser Automation"]
  budget: null
  job_type: hourly
  experience_level: intermediate
  outcome: completed
  weight: 1.0
  source: csv_import

# ─── SOCIAL MEDIA BOTS ───────────────────────────────────────────────────────
- title: "Automate SMM Panel API Purchases for Twitter & Telegram Engagement"
  description: "Build a private automation platform integrating SMM panel API to automate purchasing of likes, views, followers for Twitter and Telegram. Backend logic with optional frontend dashboard."
  category: social
  skills: ["Python", "API Integration", "SMM Panel", "Twitter API", "Telegram Bot", "Backend Development"]
  budget: null
  job_type: fixed
  experience_level: intermediate
  outcome: completed
  weight: 1.5
  source: csv_import

- title: "Build a LinkedIn Bot"
  description: "Build an app automating LinkedIn activities: connection requests, messaging, profile interactions. First LinkedIn, then Twitter."
  category: social
  skills: ["Python", "Selenium", "LinkedIn Automation", "Twitter Automation"]
  budget: null
  job_type: fixed
  experience_level: intermediate
  outcome: interested
  weight: 1.0
  source: csv_import

- title: "Project Zuckerberg — Multi-Platform E-commerce Automation"
  description: "E-commerce company with multiple websites needs a software engineer for multi-platform automation across social and e-commerce channels."
  category: social
  skills: ["Python", "Automation", "E-commerce", "Multi-platform", "Backend Development"]
  budget: null
  job_type: fixed
  experience_level: expert
  outcome: interested
  weight: 1.0
  source: csv_import

# ─── SCRAPING / AUTOMATION ───────────────────────────────────────────────────
- title: "Data Crawling and Architecture Development"
  description: "Python and Django. Crawl large amounts of data from multiple sources. Parallelise crawling, schedule crawl jobs, and design the overall architecture."
  category: automation
  skills: ["Python", "Django", "Web Scraping", "Data Pipeline", "Parallel Processing", "Scheduling"]
  budget: null
  job_type: fixed
  experience_level: expert
  outcome: completed
  weight: 1.5
  source: csv_import

- title: "LinkedIn Profile Scraper"
  description: "Extract and organise LinkedIn profile data: name, job title, connections count, education, employment history into a consistent structured format."
  category: automation
  skills: ["Python", "LinkedIn Scraper", "Data Extraction", "Web Scraping"]
  budget: null
  job_type: fixed
  experience_level: intermediate
  outcome: completed
  weight: 1.0
  source: csv_import

- title: "LinkedIn Profile and Company Scraper by Country"
  description: "NodeJS or Python scraper for LinkedIn profiles and company pages filtered by country. Store to MongoDB. Output matches provided JSON schema."
  category: automation
  skills: ["Python", "Node.js", "LinkedIn Scraping", "MongoDB", "Web Scraping"]
  budget: null
  job_type: fixed
  experience_level: intermediate
  outcome: completed
  weight: 1.0
  source: csv_import

- title: "Scrape Product Details From One Website"
  description: "Scrape product images, prices, descriptions and structured fields from a single e-commerce website. Deliver as structured CSV or JSON."
  category: automation
  skills: ["Python", "BeautifulSoup", "Selenium", "Web Scraping", "Data Extraction"]
  budget: null
  job_type: fixed
  experience_level: entry
  outcome: completed
  weight: 0.5
  source: csv_import

- title: "Scraping Tweets and Save to SQL Database"
  description: "Scrape all tweets from a list of specific Twitter fact accounts. Store results in SQL database. Handle Twitter rate limits cleanly."
  category: automation
  skills: ["Python", "Twitter API", "SQL", "Web Scraping", "PostgreSQL"]
  budget: null
  job_type: fixed
  experience_level: intermediate
  outcome: completed
  weight: 1.0
  source: csv_import

- title: "Backup Wistia Videos and Metadata to Google Drive"
  description: "Export ~1300 Wistia videos with original media, thumbnails, transcripts, and metadata to Google Drive using an automated script."
  category: automation
  skills: ["Python", "Wistia API", "Google Drive API", "Automation", "API Integration"]
  budget: null
  job_type: fixed
  experience_level: intermediate
  outcome: completed
  weight: 0.5
  source: csv_import

# ─── WEB DEVELOPMENT ─────────────────────────────────────────────────────────
- title: "Full-Stack Django Developer with CI/CD and Git Expertise"
  description: "Develop and maintain web applications using Django, Python, and JavaScript frameworks (React/Angular). Covers front-end, back-end, database management, and CI/CD pipeline setup."
  category: web
  skills: ["Python", "Django", "React", "Angular", "CI/CD", "Git", "REST API", "JavaScript"]
  budget: null
  job_type: hourly
  experience_level: expert
  outcome: completed
  weight: 1.5
  source: csv_import

- title: "AppSeed Python AI/ML Tool — Query SQLite, PostgreSQL, PDF, CSV"
  description: "Build a Python tool querying multiple data sources (SQLite, PostgreSQL, PDF, CSV) through an AI/ML query interface. Long-term engagement with iterative delivery."
  category: web
  skills: ["Python", "PostgreSQL", "SQLite", "LangChain", "OpenAI", "Data Pipelines", "API"]
  budget: null
  job_type: hourly
  experience_level: expert
  outcome: completed
  weight: 1.5
  source: csv_import

- title: "PHP Upgrade — Outdated CodeIgniter Site to PHP 7"
  description: "Upgrade an outdated CodeIgniter application to PHP 7. No new feature work."
  category: web
  skills: ["PHP", "CodeIgniter", "PHP 7 Upgrade"]
  budget: null
  job_type: fixed
  experience_level: intermediate
  outcome: completed
  weight: 0.5
  source: csv_import

# ─── AI AUTOMATION ───────────────────────────────────────────────────────────
- title: "Developer — Automated Content Creation with ChatGPT4 API"
  description: "Build a solution automating article generation using OpenAI ChatGPT4 API. Combines content scraping and AI generation pipeline."
  category: ai
  skills: ["Python", "OpenAI API", "ChatGPT", "Content Automation", "Web Scraping"]
  budget: null
  job_type: fixed
  experience_level: intermediate
  outcome: interested
  weight: 0.5
  source: csv_import

- title: "ChatGPT OpenAI Developer — Legal Contract Management AI"
  description: "Add AI capabilities to a legal contract management app. Allow users to query contracts using ChatGPT/Jasper AI."
  category: ai
  skills: ["Python", "OpenAI API", "ChatGPT", "Legal Tech", "AI Integration"]
  budget: null
  job_type: fixed
  experience_level: expert
  outcome: interested
  weight: 0.5
  source: csv_import
```

---

## 11. Changes to Existing Files

### `db/models.py`
- Add `PastJob` SQLAlchemy model (new `past_jobs` table — all columns from §6.1)
- Add `MeridianCostLog` SQLAlchemy model (new `meridian_cost_log` table — all columns from §4.3)
- Add 4 new **nullable** columns to existing `Job` model: `meridian_score` (Integer), `meridian_verdict` (String), `meridian_reasoning` (Text), `meridian_run_at` (DateTime)

### `config.py`

```python
MERIDIAN_ENABLED   = os.getenv("MERIDIAN_ENABLED", "1") == "1"
MERIDIAN_THRESHOLD = int(os.getenv("MERIDIAN_THRESHOLD", "60"))
WA_BRIDGE_URL      = os.getenv("WA_BRIDGE_URL", "http://localhost:3001/send")
WA_GROUP_JID       = os.getenv("WA_GROUP_JID", "")
PKR_PER_USD        = float(os.getenv("PKR_PER_USD", "280"))
OPENAI_API_KEY     = os.getenv("OPENAI_API_KEY", "")
OPENAI_MODEL       = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
```

### `bot/discord_bot.py` — `process_single_search()`

One block inserted **after** `channel.send()` — Discord pipeline is completely untouched above it:

```python
# ── MERIDIAN GATE (runs after Discord post — never blocks it) ──
if config.MERIDIAN_ENABLED and config.WA_GROUP_JID:
    meridian_result = await get_meridian_verdict(job, search["category"])
    score      = meridian_result.get("total_score", -1)
    verdict    = meridian_result.get("verdict", "pass")
    cost_pkr   = cost_tracker.get_last_call_cost_pkr()

    # Log every decision (non-blocking)
    asyncio.create_task(_save_meridian_result(job.get("id"), meridian_result))

    print(f"[MERIDIAN] '{job.get('title','?')[:45]}' → {score}/100 ({verdict.upper()}) ₨{cost_pkr:.4f}")

    if verdict == "pass":
        wa_msg = build_wa_job_message(job, meridian_result, search["category"], cost_pkr)
        asyncio.create_task(send_whatsapp(config.WA_GROUP_JID, wa_msg))
```

Cycle finance report appended at the end of `run_advanced_job_searches()`:

```python
# ── MERIDIAN CYCLE FINANCE REPORT ─────────────────────────────
if config.MERIDIAN_ENABLED and config.WA_GROUP_JID:
    report = cost_tracker.flush_cycle_report(jobs_scored=success_count)
    if report:
        asyncio.create_task(send_whatsapp(config.WA_GROUP_JID, report))
```

### `scraper/db_saver.py`
Update `save_jobs_to_db()` to write `meridian_score`, `meridian_verdict`, `meridian_reasoning`, `meridian_run_at` when present in the job dict.

---

## 12. Full File Responsibility Map

| File                           | Responsibility                                                          |
|--------------------------------|-------------------------------------------------------------------------|
| `meridian/engine.py`           | `build_category_summary()`, `get_category_summary()`, `run_meridian()`, `parse_gpt_response()`    |
| `meridian/prompt.py`           | `MERIDIAN_PROMPT_TEMPLATE` string constant                              |
| `meridian/whatsapp.py`         | `send_whatsapp()`, `build_wa_job_message(job, result, category, cost_pkr)` |
| `meridian/cost_tracker.py`     | `record_call()`, `flush_cycle_report()`, `get_session_total_pkr()`, `get_last_call_cost_pkr()` |
| `meridian/seeder.py`           | Load `past_jobs.yaml` → DB; `--from-csv` flag for CSV re-import         |
| `meridian/data/past_jobs.yaml` | 22-entry corpus seeded from `bitbash_projects_cleaned.csv`              |
| `whatsapp_bridge/server.js`    | Express + Baileys QR auth + POST `/send` endpoint                       |
| `whatsapp_bridge/package.json` | `@whiskeysockets/baileys`, `express`, `qrcode-terminal`                 |

---

## 13. Phase Breakdown

### Phase 1 — WhatsApp Bridge (2–3 hours)
- [ ] Create `whatsapp_bridge/` with `server.js` and `package.json`
- [ ] `npm install @whiskeysockets/baileys express qrcode-terminal`
- [ ] Run `node server.js`, scan QR, confirm session persists after restart
- [ ] Test `POST /send` with curl — verify message arrives in group
- [ ] Write and test `meridian/whatsapp.py` Python async client

### Phase 2 — Data Layer (2 hours)
- [ ] Add `PastJob` and `MeridianCostLog` models to `db/models.py`
- [ ] Add 4 nullable MERIDIAN columns to `Job` model
- [ ] Write `meridian/seeder.py`
- [ ] Place `meridian/data/past_jobs.yaml` with the 22 entries from §10
- [ ] Run seeder, verify DB rows and category distribution

### Phase 3 — Engine + Cost Tracker (2–3 hours)
- [ ] Write `meridian/prompt.py`
- [ ] Write `meridian/engine.py` (category summary + cache, async OpenAI call via `run_in_executor`, JSON parser, fail-open fallback)
- [ ] Write `meridian/cost_tracker.py`
- [ ] Unit test: run engine against 5 sample jobs, inspect scores and PKR cost output

### Phase 4 — Pipeline Integration (1–2 hours)
- [ ] Add MERIDIAN gate block to `process_single_search()` in `discord_bot.py`
- [ ] Add cycle finance report to `run_advanced_job_searches()`
- [ ] Add new env vars to `config.py` and `.env`
- [ ] Update `db_saver.py` to persist MERIDIAN fields

### Phase 5 — Shadow Mode + Tuning (48 hours after deploy)
- [ ] Deploy with `MERIDIAN_THRESHOLD=0` (all jobs that pass Discord go to WhatsApp — no filtering yet)
- [ ] Monitor score distribution in `meridian_score` column
- [ ] Set threshold to 60 once score distribution looks correct
- [ ] Continue adding entries to `past_jobs.yaml` as new work is completed

---

## 14. Risks and Mitigations

| Risk                                         | Mitigation                                                              |
|----------------------------------------------|-------------------------------------------------------------------------|
| GPT call fails / times out                   | Fail-open: Discord posts normally, WhatsApp step silently skipped       |
| Baileys session expires / WhatsApp logs out  | Bridge auto-reconnects; QR re-scan only needed after explicit logout    |
| WhatsApp bridge not running (port closed)    | Python client catches `httpx.ConnectError`, logs warning, continues     |
| Category corpus empty for a new category     | Engine returns `verdict=pass, score=-1`, logs warning, does not crash   |
| GPT returns malformed JSON                   | Robust JSON parser with regex fallback; defaults to `verdict=pass`      |
| OpenAI rate limits across many keywords      | Dedicated semaphore (reuse `_upwork_semaphore` or own limit of 3)       |
| PKR rate becomes stale                       | Manual `.env` update; all cost figures are informational only           |
| Threshold too aggressive — drops real wins   | Shadow mode first; activate real threshold only after reviewing data    |

---

## 15. Success Criteria (1 Week Post-Deploy)

1. WhatsApp group receives only relevant, high-signal jobs — measurably less noise than Discord
2. Finance report arrives every scan cycle with correct PKR cost per cycle and session total
3. Zero missed high-value jobs — confirmed by spot-checking `meridian_verdict='skip'` rows in DB
4. All decisions logged with score breakdown + reasoning (full audit trail in `jobs` table)
5. Category corpus active for all 7 categories with accurate, category-specific scoring

---

*MERIDIAN — built on what you already know, filters what you don't need, reaches you where you are.*

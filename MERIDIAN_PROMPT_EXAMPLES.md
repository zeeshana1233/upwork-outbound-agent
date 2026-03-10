# MERIDIAN — Exact OpenAI Prompt & Response Examples

**Model:** `gpt-4o-mini`  
**System role:** `user` (single message, no separate system prompt)  
**Pass threshold:** `60 / 100`  
**Score weights:** Domain 40 · Clarity 25 · Tech 20 · Budget 15

> ⚠️ **Note on stored scores/reasoning:** The 3 jobs below were originally scored with the **wrong** corpus (all categories pointed to `automation`). That bug is now fixed. The stored scores (28, 82, 32) and stored reasoning still reflect the old broken run. The prompts shown here are the **corrected** prompts — what OpenAI will receive from the next run onward with the correct corpus per category.

---

## Category → Corpus → Discord Channel mapping (fixed)

| Keyword `category` | Discord channel | Past jobs in corpus |
|---|---|---|
| `Android Automation` | `#appilot` | 2 jobs — Android device/emulator farms |
| `Stealth Automation` | `#stealth-mode` | 5 jobs — Multilogin, GoLogin, fingerprint spoofing |
| `Social Media & SMM` | `#smm-bots` | 3 jobs — SMM panel, LinkedIn bot, multi-platform |
| `Automation` | `#automation` | 6 jobs — scrapers, crawlers, data pipelines |
| `Web Development` | `#web-dev` | 3 jobs — Django, AppSeed, PHP |
| `AI Automation` | `#ai-automation` | 2 jobs — ChatGPT API, legal contract AI |
| `TikTok Shop` | `#tiktok-shop` | 0 jobs (add when ready) |

---

---

# EXAMPLE 1 — SKIP (Score: 28 / 100)
**Job came through:** `#web-dev` channel → category `Web Development`

## → Prompt sent to OpenAI

```
You are a job relevance filter for a freelancer.

== PAST WORK REFERENCE: Web Development ==
Reference work we have done in this category:

1. "Full-Stack Django Developer with CI/CD and Git Expertise"
   Develop and maintain web applications using Django, Python, and JavaScript frameworks (React/Angular). Covers front-end, back-end, database management, and CI/CD pipeline setup.
   Skills: Python, Django, React, Angular, CI/CD, Git, REST API, JavaScript
   Budget: unknown  |  Outcome: completed

2. "AppSeed Python AI/ML Tool — Query SQLite, PostgreSQL, PDF, CSV"
   Build a Python tool querying multiple data sources (SQLite, PostgreSQL, PDF, CSV) through an AI/ML query interface. Long-term engagement with iterative delivery.
   Skills: Python, PostgreSQL, SQLite, LangChain, OpenAI, Data Pipelines, API
   Budget: unknown  |  Outcome: completed

3. "PHP Upgrade — Outdated CodeIgniter Site to PHP 7"
   Upgrade an outdated CodeIgniter application to PHP 7. No new feature work.
   Skills: PHP, CodeIgniter, PHP 7 Upgrade
   Budget: unknown  |  Outcome: completed


== INCOMING JOB ==
Title: Shopify Web Designer Needed to Build High-Converting Industry Application Pages
Description: We are revamping our Shopify website to move from text block heavy pages to structured, high-converting industry solution pages.

I am looking for a Shopify designer who can take the content and images I provide and turn them into polished, professional, conversion-focused application pages.

This is primarily a design and layout project. All written content and images will be provided. Your job is to elevate the presentation and user experience inside Shopify. I am open to suggestions.

Primary Goal:
Turn our application pages into the strongest conversion assets on the site. These pages shou
Required Skills: Shopify, Web & Mobile Design Consultation, UX & UI, Web Design, Shopify Theme
Budget: Not specified

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

## ← Expected response from OpenAI

```json
{
  "domain_fit": 8,
  "scope_clarity": 15,
  "tech_stack_match": 0,
  "budget_viability": 8,
  "total_score": 28,
  "verdict": "skip",
  "reasoning": "Shopify design and UI layout has no domain overlap with our Python/Django web development background. We build backends, APIs, and data tools — not front-end Shopify themes. Domain mismatch is too large to overcome."
}
```

**Why SKIP:** Our Web Development corpus is Django/Python/API backends. Shopify theme design is pure front-end UI — zero tech overlap. Domain Fit ~8/40, Tech Stack 0/20.

---

---

# EXAMPLE 2 — PASS (Score: 82 / 100)
**Job came through:** `#automation` channel → category `Automation`

## → Prompt sent to OpenAI

```
You are a job relevance filter for a freelancer.

== PAST WORK REFERENCE: Automation ==
Reference work we have done in this category:

1. "Data Crawling and Architecture Development"
   Python and Django. Crawl large amounts of data from multiple sources. Parallelise crawling, schedule crawl jobs, and design the overall architecture.
   Skills: Python, Django, Web Scraping, Data Pipeline, Parallel Processing, Scheduling
   Budget: unknown  |  Outcome: completed

2. "LinkedIn Profile Scraper"
   Extract and organise LinkedIn profile data: name, job title, connections count, education, employment history into a consistent structured format.
   Skills: Python, LinkedIn Scraper, Data Extraction, Web Scraping
   Budget: unknown  |  Outcome: completed

3. "LinkedIn Profile and Company Scraper by Country"
   NodeJS or Python scraper for LinkedIn profiles and company pages filtered by country. Store to MongoDB. Output matches provided JSON schema.
   Skills: Python, Node.js, LinkedIn Scraping, MongoDB, Web Scraping
   Budget: unknown  |  Outcome: completed

4. "Scraping Tweets and Save to SQL Database"
   Scrape all tweets from a list of specific Twitter fact accounts. Store results in SQL database. Handle Twitter rate limits cleanly.
   Skills: Python, Twitter API, SQL, Web Scraping, PostgreSQL
   Budget: unknown  |  Outcome: completed

5. "Scrape Product Details From One Website"
   Scrape product images, prices, descriptions and structured fields from a single e-commerce website. Deliver as structured CSV or JSON.
   Skills: Python, BeautifulSoup, Selenium, Web Scraping, Data Extraction
   Budget: unknown  |  Outcome: completed

6. "Backup Wistia Videos and Metadata to Google Drive"
   Export ~1300 Wistia videos with original media, thumbnails, transcripts, and metadata to Google Drive using an automated script.
   Skills: Python, Wistia API, Google Drive API, Automation, API Integration
   Budget: unknown  |  Outcome: completed


== INCOMING JOB ==
Title: Web Scraping Expert - Selenium, Django, Playwright
Description: We run combination of playwright, selenium/chrome, and requests/API based scrapers w/ rotating proxies. Scheduling and execution is done on Django, and the scrapers themselves run off Redis/Celery workers.

I need someone with immediate availability to get these sorted in the next week, and then lesser long term maintenance if you're still interested.

Let me know, thank you
Required Skills: Python, Data Scraping, Selenium WebDriver, Selenium
Budget: $50.0 (Fixed Price)

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

## ← Response returned by OpenAI (actual stored)

```json
{
  "domain_fit": 38,
  "scope_clarity": 18,
  "tech_stack_match": 18,
  "budget_viability": 8,
  "total_score": 82,
  "verdict": "pass",
  "reasoning": "The job aligns well with web scraping, which is relevant to automation. The requirements are clearly defined, and while the tech stack has some overlap, the budget is realistic for the work involved."
}
```

**Why PASS:** Playwright + Selenium + Django + Redis/Celery = direct match to past work. Domain Fit 38/40. `$50 Fixed Price` is low but budget stays neutral at 8/15.

---

---

# EXAMPLE 3 — SKIP (Score: 32 / 100)
**Job came through:** `#smm-bots` channel → category `Social Media & SMM`

## → Prompt sent to OpenAI

```
You are a job relevance filter for a freelancer.

== PAST WORK REFERENCE: Social Media & SMM ==
Reference work we have done in this category:

1. "Automate SMM Panel API Purchases for Twitter & Telegram Engagement"
   Build a private automation platform integrating SMM panel API to automate purchasing of likes, views, followers for Twitter and Telegram. Backend logic with optional frontend dashboard.
   Skills: Python, API Integration, SMM Panel, Twitter API, Telegram Bot, Backend Development
   Budget: unknown  |  Outcome: completed

2. "Build a LinkedIn Bot"
   Build an app automating LinkedIn activities: connection requests, messaging, profile interactions. First LinkedIn, then Twitter.
   Skills: Python, Selenium, LinkedIn Automation, Twitter Automation
   Budget: unknown  |  Outcome: interested

3. "Project Zuckerberg — Multi-Platform E-commerce Automation"
   E-commerce company with multiple websites needs a software engineer for multi-platform automation across social and e-commerce channels.
   Skills: Python, Automation, E-commerce, Multi-platform, Backend Development
   Budget: unknown  |  Outcome: interested


== INCOMING JOB ==
Title: Cinematic Launch Video for African Livestock
Description: We are launching a livestock security technology platform in Botswana called Kgomo Khumo.

We want a cinematic promotional video (60-90 seconds) that combines:

• Botswana landscapes
• Cattle farming visuals
• Futuristic technology graphics
• Mobile app interface demonstration
• National pride colors inspired by the Botswana flag

The video should feel like a cinematic technology launch similar to Tesla or Apple product videos.

Before hiring we would like to see examples of cinematic videos you have previously created.

Deliverables:
• 60-90 second promotional video
• Motion graphics and logo
Required Skills: Video Editing, Video Production, Animation, Video Commercial, Motion Graphics
Budget: $300.0 (Fixed Price)

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

## ← Expected response from OpenAI

```json
{
  "domain_fit": 0,
  "scope_clarity": 22,
  "tech_stack_match": 0,
  "budget_viability": 10,
  "total_score": 32,
  "verdict": "skip",
  "reasoning": "Video production and motion graphics have no overlap with our SMM automation work. We build bots and APIs — not promotional videos. Domain mismatch is total despite a well-scoped brief."
}
```

**Why SKIP:** Social Media & SMM corpus is Python bots, API integrations, Selenium. Video editing/motion graphics = 0 tech overlap, 0 domain overlap. A clear scope (22/25) cannot save it.

---

---

## Score Breakdown Summary

| Job Title | Category | Corpus used | Domain | Clarity | Tech | Budget | **Total** | Verdict |
|---|---|---|---|---|---|---|---|---|
| Shopify Web Designer | Web Development | Django/PHP/AppSeed | 8/40 | 15/25 | 0/20 | 8/15 | **28** | ❌ SKIP |
| Web Scraping (Selenium/Django) | Automation | Scrapers/crawlers | 38/40 | 18/25 | 18/20 | 8/15 | **82** | ✅ PASS |
| Cinematic Launch Video | Social Media & SMM | SMM bots/LinkedIn | 0/40 | 22/25 | 0/20 | 10/15 | **32** | ❌ SKIP |

---

## What changed vs the old (broken) run

| Before fix | After fix |
|---|---|
| All categories used `automation` corpus | Each category uses its own correct corpus |
| Shopify job compared to scraping/Django jobs | Shopify job compared to Django/Python web corpus |
| Cinematic Video compared to scraping jobs | Cinematic Video compared to SMM bots corpus |
| Reasoning said "outside domain of Android automation" | Reasoning is now tied to actual category corpus |

---

## Key observations

- **Domain Fit (0-40) is the deciding factor.** Controls ~40% of the score alone.
- **Correct corpus = correct scoring.** The Shopify job now correctly fails against the *web dev* corpus (our web work is Python backends, not Shopify design). Previously it failed against scrapers which was just noise.
- **Budget type now included.** `$50.0 (Fixed Price)` gives GPT accurate context vs raw `50.0`.
- **Corpus quality matters.** Add more past jobs to `meridian/data/past_jobs.yaml` and reseed with `python -m meridian.seeder` to improve accuracy per category.

# LAST MERIDIAN PROMPT
Job: Automation to Extract Property Listings and Upload to my website
Category: Automation
Saved: 2026-03-10 18:48:23 UTC

---

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
Title: Automation to Extract Property Listings and Upload to my website
Description: I am a real estate agent and I regularly copy property listings from a property viewer website and then manually upload them to my website. I would like a freelancer to build a simple automation that performs this process automatically.

The automation must run locally on my Windows computer, and I must have full control of it after delivery. I do not want a cloud service or anything dependent on the developer after completion.

I want to reduce manual work when transferring listings between websites. The automation should reliably process multiple properties and prepare Idealista listings quickly.

Automation Requirements
The automation should:
1. Open the property viewer page.
2. Detect all properties displayed on the page.
3. Loop through each property listing.
4. For each property:
- Click the property image to open the property details.
- Download all property photos.
- Extract the following information if available:
- property title
- property description
- price
- bedrooms
- bathrooms
- square meters
- any other property specifications visible.
5. Save the data locally:
- Create a folder per property.
- Save all photos in that folder.
- Save the extracted text in a structured file (Excel, Word, or text file).

More details upon request.
Required Skills: Automation, Data Scraping, Web Development
Budget: $10.0-$15.0/hr (Hourly)

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
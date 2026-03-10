"""
data_audit_test.py
------------------
One-shot script: fetch 3 live Upwork jobs using the existing scraper stack,
print EVERY field returned by both the search query AND the job-details query,
then summarise what is / isn't available.

Run:
    python data_audit_test.py
"""

import asyncio
import json
import sys
import os

# ── make imports work from project root ────────────────────────────────────
sys.path.insert(0, os.path.dirname(__file__))

# ── config (reads .env automatically via config.py) ─────────────────────────
import config  # noqa — triggers load_dotenv() so env vars are available

# ── scraper layer ────────────────────────────────────────────────────────────
from scraper.upwork_scraper import UpworkScraper
from scraper.job_search import fetch_jobs
from scraper.job_details import fetch_job_details

DIVIDER = "=" * 70


def pp(label, value):
    """Pretty-print a single field."""
    if isinstance(value, (dict, list)):
        v = json.dumps(value, indent=2, default=str)
    else:
        v = str(value) if value is not None else "— not available —"
    # truncate very long strings
    if len(v) > 500:
        v = v[:500] + "  [TRUNCATED]"
    print(f"  {label:40s}: {v}")


async def main():
    print(DIVIDER)
    print("  UPWORK DATA AUDIT — field inventory test")
    print(DIVIDER)

    # ------------------------------------------------------------------
    # 1.  Init scraper
    # ------------------------------------------------------------------
    scraper = UpworkScraper()
    print("\n[1] Scraper initialised")

    # ------------------------------------------------------------------
    # 2.  Search: grab up to 5 jobs for a broad query
    # ------------------------------------------------------------------
    TEST_QUERY = "web scraping python"
    print(f"\n[2] Fetching jobs for query: '{TEST_QUERY}'")
    jobs = await fetch_jobs(
        scraper,
        query=TEST_QUERY,
        limit=5,
        delay=False,
        filters={"contractor_tier": ["1", "2", "3"]}   # all tiers for testing
    )
    print(f"    → {len(jobs)} jobs returned after filters\n")

    if not jobs:
        print("No jobs returned — aborting test.")
        return

    # ------------------------------------------------------------------
    # 3b.  RAW PROBE: post absolute-minimum query — use scraper.scraper (cloudscraper)
    # ------------------------------------------------------------------
    print("\n" + DIVIDER)
    print("  RAW PROBE — minimum details query (category + description only)")
    print(DIVIDER)
    import json as _json
    min_query = {
        "alias": "gql-query-get-visitor-job-details",
        "query": """
        query JobPubDetailsQuery($id: ID!) {
            jobPubDetails(id: $id) {
                opening {
                    description
                    postedOn
                    category { name }
                    categoryGroup { name }
                    contractorTier
                    workload
                    budget { amount currencyCode }
                    extendedBudgetInfo { hourlyBudgetMin hourlyBudgetMax }
                    engagementDuration { label weeks }
                    clientActivity { totalApplicants totalHired }
                }
                buyer {
                    location { city country countryTimezone }
                    jobs { openCount }
                }
            }
        }
        """,
        "variables": {"id": jobs[0]["id"]}
    }
    url = scraper.JOB_DETAILS_URL
    scraper._generate_session_ids()
    headers = scraper._get_current_headers()
    cookies = scraper._get_current_cookies()
    try:
        resp = scraper.scraper.post(url, headers=headers, cookies=cookies,
                                    data=_json.dumps(min_query), timeout=30)
        print(f"  Status: {resp.status_code}")
        try:
            raw = resp.json()
        except Exception as je:
            print(f"  Response body (first 500 chars): {resp.text[:500]}")
            raise je
        if "errors" in raw:
            print(f"  Errors: {[e.get('message','?') for e in raw['errors']]}")
        if raw.get("data"):
            print(f"  ✅ Partial data found! Keys: {list(raw['data'].keys())}")
            opening = (raw["data"].get("jobPubDetails") or {}).get("opening") or {}
            buyer   = (raw["data"].get("jobPubDetails") or {}).get("buyer") or {}
            print(f"\n  --- Partial fields actually returned ---")
            pp("category",           (opening.get("category") or {}).get("name"))
            pp("category_group",     (opening.get("categoryGroup") or {}).get("name"))
            pp("description (first 300 chars)", (opening.get("description") or "")[:300])
            pp("postedOn",           opening.get("postedOn"))
            pp("contractorTier",     opening.get("contractorTier"))
            pp("workload",           opening.get("workload"))
            pp("budget",             opening.get("budget"))
            pp("extendedBudgetInfo", opening.get("extendedBudgetInfo"))
            pp("engagementDuration", opening.get("engagementDuration"))
            pp("clientActivity",     opening.get("clientActivity"))
            pp("buyer.location",     buyer.get("location"))
            pp("buyer.jobs",         buyer.get("jobs"))
        else:
            print("  ❌ No data at all — full response:")
            print(f"  {_json.dumps(raw, indent=2)[:1000]}")
    except Exception as probe_err:
        print(f"  ❌ Probe failed: {probe_err}")

    # ------------------------------------------------------------------
    # 3.  Show SEARCH-LAYER fields for every job
    # ------------------------------------------------------------------
    print(DIVIDER)
    print("  FIELDS FROM SEARCH QUERY (job_search.py / extract_jobs_from_response)")
    print(DIVIDER)
    SEARCH_FIELDS = [
        "id", "title", "description",
        "createdDateTime", "publishTime", "sourcingTimestamp",
        "client", "budget", "budget_numeric",
        "total_applicants", "amount", "hourly_min", "hourly_max",
        "weekly_budget", "duration", "duration_label",
        "engagement", "experience_level", "applied",
        "category", "category_group", "job_type", "skills",
    ]
    for idx, job in enumerate(jobs[:3], 1):
        print(f"\n--- Search result #{idx}: {job.get('title','?')[:60]} ---")
        for field in SEARCH_FIELDS:
            pp(field, job.get(field))

    # ------------------------------------------------------------------
    # 4.  Fetch FULL DETAILS for the first two jobs
    # ------------------------------------------------------------------
    print("\n" + DIVIDER)
    print("  FIELDS FROM JOB DETAILS QUERY (job_details.py / fetch_job_details)")
    print(DIVIDER)
    DETAIL_FIELDS = [
        # identity
        "id", "ciphertext", "title",
        # content
        "description", "status", "posted_on", "publish_time",
        # job shape
        "workload", "contractor_tier", "job_type",
        "engagement_duration", "engagement_weeks",
        # money
        "budget", "budget_amount", "hourly_budget_min", "hourly_budget_max",
        "budget_type", "currency_code",
        # *** THE CATEGORY FIELDS — key for Module 3 ***
        "category", "category_group",
        # skills / tools
        "skills", "tools",
        # activity
        "total_applicants", "total_hired", "total_interviewed",
        "positions_to_hire",
        # client
        "client_location", "client_country", "client_timezone",
        "client_total_assignments", "client_active_assignments",
        "client_hours", "client_feedback_count", "client_rating",
        "client_total_jobs", "client_total_spent", "client_open_jobs",
        "client_industry", "client_company_size",
        # requirements / flags
        "payment_verified", "min_job_success_score", "min_hours",
        "min_hours_week", "english_requirement", "rising_talent",
        "portfolio_required",
        # extras
        "deadline", "deliverables", "similar_jobs_count",
    ]

    for idx, job in enumerate(jobs[:2], 1):
        job_id = job.get("id")
        print(f"\n--- Detail fetch #{idx}: {job.get('title','?')[:60]} (id={job_id}) ---")
        details = await fetch_job_details(scraper, job_id, max_retries=1)
        if not details:
            print("  ⚠  fetch_job_details returned None (auth / API error)")
            continue
        for field in DETAIL_FIELDS:
            pp(field, details.get(field))

    # ------------------------------------------------------------------
    # 5.  SKILLS & DB SAVE TEST — verify new db_saver stores skills + full desc
    # ------------------------------------------------------------------
    print("\n" + DIVIDER)
    print("  TASK 3 — SKILLS & DATABASE VERIFICATION")
    print(DIVIDER)

    # 5a.  Confirm skills appear in live search results
    print("\n  [5a] Skills present in search results:")
    for j in jobs:
        skill_list = j.get("skills") or []
        print(f"       {j['title'][:50]}")
        print(f"         skills ({len(skill_list)}): {', '.join(skill_list) or '— none —'}")
        print(f"         description length: {len(j.get('description') or '')} chars")

    # 5b.  Save the fetched jobs using the NEW db_saver and read back
    print("\n  [5b] Saving to DB via updated db_saver + reading back:")
    from scraper.db_saver import save_jobs_to_db
    save_jobs_to_db(jobs)   # already-existing jobs are skipped; new ones saved

    try:
        from db.database import SessionLocal
        from db.models import Job
        import json as _json_db
        session_db = SessionLocal()
        recent_jobs_db = session_db.query(Job).order_by(Job.id.desc()).limit(3).all()
        print(f"\n  Latest 3 rows in DB:")
        for r in recent_jobs_db:
            skills_decoded = []
            if r.skills:
                try:
                    skills_decoded = _json_db.loads(r.skills)
                except Exception:
                    skills_decoded = [r.skills]
            print(f"\n    job_id  : {r.job_id}")
            print(f"    title   : {r.title}")
            print(f"    budget  : {r.budget}")
            print(f"    desc len: {len(r.description or '')} chars")
            desc_preview = (r.description or '')[:200]
            print(f"    desc    : {desc_preview}{'...' if len(r.description or '') > 200 else ''}")
            print(f"    skills  : {skills_decoded}")
        session_db.close()
    except Exception as db_err:
        print(f"  ❌ DB read error: {db_err}")

    print("\n" + DIVIDER)
    print("  TEST COMPLETE")
    print(DIVIDER)


if __name__ == "__main__":
    asyncio.run(main())

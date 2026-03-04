# scraper/job_details.py
"""
Handles job details fetching and parsing for UpworkScraper.
Uses the scraper's existing session (same as job_search.py) — no separate
headers files, no authbot dependency.
"""

import json
import asyncio
import random


# Re-use the same semaphore from job_search so total concurrency stays bounded.
from .job_search import _upwork_semaphore, _token_refresh_lock


async def fetch_job_details(scraper, job_id, max_retries=3):
    """
    Fetch job details via the visitor GraphQL API, reusing the scraper's
    existing cloudscraper session, headers, and cookies (same approach as
    make_graphql_request in job_search.py).

    Returns a dict with job details (including ``payment_verified``) on
    success, or ``None`` on unrecoverable failure.
    """
    clean_job_id = str(job_id).lstrip("~")
    formatted_job_id = f"~{clean_job_id}"
    print(f"[Job Details] Fetching details for {formatted_job_id}")

    payload = get_simplified_job_details_query(formatted_job_id)
    url = scraper.JOB_DETAILS_URL  # gql-query-get-visitor-job-details

    for attempt in range(max_retries):
        try:
            scraper._generate_session_ids()
            headers = scraper._get_current_headers()
            cookies = scraper._get_current_cookies()
            data_str = json.dumps(payload)

            loop = asyncio.get_event_loop()

            async with _upwork_semaphore:
                response = await loop.run_in_executor(
                    None,
                    lambda: scraper.scraper.post(
                        url,
                        headers=headers,
                        cookies=cookies,
                        data=data_str,
                        timeout=30,
                    ),
                )

            print(f"[Job Details] Response status: {response.status_code} (attempt {attempt + 1}/{max_retries})")

            # ── 401 / 403 — token refresh ──────────────────────────────
            if response.status_code in (401, 403):
                print(f"[Job Details] Auth error {response.status_code}, refreshing tokens…")
                if attempt < max_retries - 1:
                    async with _token_refresh_lock:
                        scraper._refresh_tokens()
                    await asyncio.sleep(random.uniform(2, 4))
                    continue
                print("[Job Details] ❌ Max retries on auth error")
                return None

            # ── Other non-200 ──────────────────────────────────────────
            if response.status_code != 200:
                print(f"[Job Details] API error {response.status_code}: {response.text[:300]}")
                if attempt < max_retries - 1:
                    await asyncio.sleep(random.uniform(1, 3))
                    continue
                return None

            # ── Parse JSON ─────────────────────────────────────────────
            data = response.json()

            if "errors" in data:
                for err in data["errors"]:
                    print(f"[Job Details] GraphQL error: {err.get('message', '?')}")
                raw_data = data.get("data") or {}
                if raw_data and raw_data.get("jobPubDetails"):
                    print("[Job Details] ⚠ Partial data available alongside errors — attempting parse")
                else:
                    print(f"[Job Details] Raw response keys: {list(data.keys())} | data keys: {list(raw_data.keys()) if raw_data else 'none'}")
                    return None

            details = extract_job_details_from_response(data)
            if details:
                print(f"[Job Details] ✅ Fetched: {details.get('title', '?')[:60]}")
            return details

        except Exception as exc:
            print(f"[Job Details] ❌ Exception: {exc}")
            if attempt < max_retries - 1:
                await asyncio.sleep(random.uniform(1, 3))
                continue
            return None

    return None

def get_simplified_job_details_query(job_id):
    """
    Visitor-only query — requests ONLY fields accessible without OAuth2.
    Removed: buyer.stats, qualifications, buyerExtra (all require privileged scope).
    Kept:    opening.* (fully public), buyer.location, buyer.jobs.openCount.
    """
    VISITOR_QUERY = """
    query JobPubDetailsQuery($id: ID!) {
        jobPubDetails(id: $id) {
            opening {
                status
                postedOn
                publishTime
                workload
                contractorTier
                description
                info {
                    ciphertext
                    id
                    type
                    title
                    createdOn
                    premium
                }
                sandsData {
                    ontologySkills {
                        id
                        prefLabel
                    }
                    additionalSkills {
                        id
                        prefLabel
                    }
                }
                category {
                    name
                }
                categoryGroup {
                    name
                }
                budget {
                    amount
                    currencyCode
                }
                engagementDuration {
                    label
                    weeks
                }
                extendedBudgetInfo {
                    hourlyBudgetMin
                    hourlyBudgetMax
                    hourlyBudgetType
                }
                clientActivity {
                    totalApplicants
                    totalHired
                    totalInvitedToInterview
                    numberOfPositionsToHire
                }
                tools {
                    name
                }
            }
            buyer {
                location {
                    city
                    country
                    countryTimezone
                }
                jobs {
                    openCount
                }
            }
        }
    }
    """
    return {
        "alias": "gql-query-get-visitor-job-details",
        "query": VISITOR_QUERY,
        "variables": {
            "id": job_id
        }
    }

def extract_job_details_from_response(data):
    from datetime import datetime
    try:
        job_pub_details = data.get("data", {}).get("jobPubDetails", {})
        if not job_pub_details:
            print("[Job Details] No jobPubDetails found in response")
            return {
                "id": data.get("data", {}).get("id") or data.get("id", ""),
                "title": data.get("data", {}).get("title") or data.get("title", "No title"),
                "description": "No details available."
            }

        opening          = job_pub_details.get("opening") or {}
        buyer            = job_pub_details.get("buyer") or {}
        info             = opening.get("info") or {}
        extended_budget  = opening.get("extendedBudgetInfo") or {}
        client_activity  = opening.get("clientActivity") or {}
        category         = opening.get("category") or {}
        category_group   = opening.get("categoryGroup") or {}
        budget_info      = opening.get("budget") or {}
        engagement_duration = opening.get("engagementDuration") or {}
        sands_data       = opening.get("sandsData") or {}
        buyer_location   = buyer.get("location") or {}
        buyer_jobs       = buyer.get("jobs") or {}

        # ── Skills: merge additionalSkills + ontologySkills (deduplicated) ──
        seen_skills = set()
        skills = []
        for section in ("additionalSkills", "ontologySkills"):
            for skill in (sands_data.get(section) or []):
                label = (skill or {}).get("prefLabel", "")
                if label and label not in seen_skills:
                    seen_skills.add(label)
                    skills.append(label)

        # ── Budget ──────────────────────────────────────────────────────────
        budget_display = "Not specified"
        hourly_min = extended_budget.get("hourlyBudgetMin")
        hourly_max = extended_budget.get("hourlyBudgetMax")
        budget_amount = budget_info.get("amount")
        try:
            if budget_amount and float(budget_amount) > 0:
                budget_display = f"${float(budget_amount):,.0f}"
            elif hourly_min and float(hourly_min) > 0:
                if hourly_max and float(hourly_max) > 0:
                    budget_display = f"${hourly_min}-${hourly_max}/hr"
                else:
                    budget_display = f"${hourly_min}+/hr"
        except Exception:
            pass

        # ── Client location ─────────────────────────────────────────────────
        client_location_str = "Not specified"
        if buyer_location.get("city") and buyer_location.get("country"):
            client_location_str = f"{buyer_location['city']}, {buyer_location['country']}"
        elif buyer_location.get("country"):
            client_location_str = buyer_location["country"]

        # ── Posted time ─────────────────────────────────────────────────────
        posted_on = opening.get("postedOn", "")
        if posted_on:
            try:
                posted_date = datetime.fromisoformat(posted_on.replace("Z", "+00:00"))
                posted_time = posted_date.strftime("%Y-%m-%d %H:%M UTC")
            except Exception:
                posted_time = posted_on
        else:
            posted_time = "Unknown"

        job_details = {
            # ── Identity ──────────────────────────────────────────────────
            "id":                   info.get("id"),
            "ciphertext":           info.get("ciphertext"),
            "title":                info.get("title"),
            # ── Content ───────────────────────────────────────────────────
            "description":          opening.get("description"),
            "status":               opening.get("status"),
            "posted_on":            posted_time,
            "publish_time":         opening.get("publishTime"),
            "workload":             opening.get("workload"),
            "contractor_tier":      opening.get("contractorTier"),
            "job_type":             info.get("type"),
            # ── Budget ────────────────────────────────────────────────────
            "budget":               budget_display,
            "budget_amount":        budget_amount,
            "hourly_budget_min":    hourly_min,
            "hourly_budget_max":    hourly_max,
            "budget_type":          extended_budget.get("hourlyBudgetType"),
            "currency_code":        budget_info.get("currencyCode"),
            # ── Duration ──────────────────────────────────────────────────
            "engagement_duration":  engagement_duration.get("label"),
            "engagement_weeks":     engagement_duration.get("weeks"),
            # ── CATEGORY (key for Module 3) ───────────────────────────────
            "category":             category.get("name"),       # e.g. "Web Development"
            "category_group":       category_group.get("name"), # e.g. "Engineering & Technology"
            # ── Skills & Tools ────────────────────────────────────────────
            "skills":               skills,
            "tools":                [t.get("name", "") for t in (opening.get("tools") or [])],
            # ── Activity ──────────────────────────────────────────────────
            "total_applicants":     client_activity.get("totalApplicants"),
            "total_hired":          client_activity.get("totalHired"),
            "total_interviewed":    client_activity.get("totalInvitedToInterview"),
            "positions_to_hire":    client_activity.get("numberOfPositionsToHire"),
            # ── Client (visitor-accessible fields only) ───────────────────
            "client_location":      client_location_str,
            "client_country":       buyer_location.get("country"),
            "client_timezone":      buyer_location.get("countryTimezone"),
            "client_open_jobs":     buyer_jobs.get("openCount"),
            # ── OAuth2-restricted fields — always None (visitor API) ──────
            "payment_verified":     None,   # requires OAuth2 — skipped
            "client_total_spent":   None,   # requires OAuth2 — skipped
            "client_rating":        None,   # requires OAuth2 — skipped
            "client_feedback_count": None,  # requires OAuth2 — skipped
            "client_total_assignments": None,
            "client_total_jobs":    None,
            "client_hours":         None,
            "min_job_success_score": None,
            "english_requirement":  None,
            "rising_talent":        None,
            "portfolio_required":   None,
        }

        return job_details

    except Exception as e:
        print(f"[Job Details] ❌ Error extracting job details: {e}")
        import traceback
        traceback.print_exc()
        return {
            "id":          data.get("data", {}).get("id") or data.get("id", ""),
            "title":       data.get("data", {}).get("title") or data.get("title", "No title"),
            "description": f"Error: {e}"
        }
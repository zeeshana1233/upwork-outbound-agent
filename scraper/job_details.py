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
                if not data.get("data"):
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
    return {
        "alias": "gql-query-get-visitor-job-details",
        "query": """query JobPubDetailsQuery($id: ID!) {\n                jobPubDetails(id: $id) {\n                    opening {\n                        status\n                        postedOn\n                        publishTime\n                        workload\n                        contractorTier\n                        description\n                        info {\n                            ciphertext\n                            id\n                            type\n                            title\n                            createdOn\n                            premium\n                        }\n                        sandsData {\n                            ontologySkills {\n                                id\n                                prefLabel\n                            }\n                            additionalSkills {\n                                id\n                                prefLabel\n                            }\n                        }\n                        category {\n                            name\n                        }\n                        categoryGroup {\n                            name\n                        }\n                        budget {\n                            amount\n                            currencyCode\n                        }\n                        engagementDuration {\n                            label\n                            weeks\n                        }\n                        extendedBudgetInfo {\n                            hourlyBudgetMin\n                            hourlyBudgetMax\n                            hourlyBudgetType\n                        }\n                        clientActivity {\n                            totalApplicants\n                            totalHired\n                            totalInvitedToInterview\n                            numberOfPositionsToHire\n                        }\n                        tools {\n                            name\n                        }\n                    }\n                    buyer {\n                        location {\n                            city\n                            country\n                            countryTimezone\n                        }\n                        stats {\n                            totalAssignments\n                            feedbackCount\n                            score\n                            totalJobsWithHires\n                            totalCharges {\n                                amount\n                                currencyCode\n                            }\n                            hoursCount\n                        }\n                        jobs {\n                            openCount\n                        }\n                    }\n                    qualifications {\n                        minJobSuccessScore\n                        minOdeskHours\n                        prefEnglishSkill\n                        risingTalent\n                        shouldHavePortfolio\n                    }\n                    buyerExtra {\n                        isPaymentMethodVerified\n                    }\n                }\n            }""",
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
        
        opening = job_pub_details.get("opening") or {}
        buyer = job_pub_details.get("buyer") or {}
        qualifications = job_pub_details.get("qualifications") or {}
        buyer_extra = job_pub_details.get("buyerExtra") or {}
        similar_jobs = job_pub_details.get("similarJobs") or []
        info = opening.get("info") or {}
        extended_budget = opening.get("extendedBudgetInfo") or {}
        client_activity = opening.get("clientActivity") or {}
        category = opening.get("category") or {}
        category_group = opening.get("categoryGroup") or {}
        budget_info = opening.get("budget") or {}
        engagement_duration = opening.get("engagementDuration") or {}
        sands_data = opening.get("sandsData") or {}
        buyer_location = buyer.get("location") or {}
        buyer_stats = buyer.get("stats") or {}
        buyer_company = buyer.get("company") or {}
        buyer_jobs = buyer.get("jobs") or {}
        
        # Handle total_charges
        total_charges = buyer_stats.get("totalCharges", {})
        client_total_spent_value = None
        if total_charges and isinstance(total_charges, dict):
            client_total_spent_value = total_charges.get("amount")
        
        # Extract skills
        skills = []
        additional_skills = sands_data.get("additionalSkills") or []
        for skill in additional_skills:
            if skill and skill.get("prefLabel"):
                skills.append(skill["prefLabel"])
        ontology_skills = sands_data.get("ontologySkills") or []
        for skill in ontology_skills:
            if skill and skill.get("prefLabel"):
                skills.append(skill["prefLabel"])
        
        # Format budget
        budget_display = "Not specified"
        hourly_min = extended_budget.get("hourlyBudgetMin")
        hourly_max = extended_budget.get("hourlyBudgetMax")
        budget_amount = budget_info.get("amount")
        try:
            if budget_amount and float(budget_amount) > 0:
                budget_display = f"${budget_amount:,.0f}"
            elif hourly_min and float(hourly_min) > 0:
                if hourly_max and float(hourly_max) > 0:
                    budget_display = f"${hourly_min}-${hourly_max}/hr"
                else:
                    budget_display = f"${hourly_min}+/hr"
        except Exception:
            pass
        
        # Format location
        client_location_str = "Not specified"
        if buyer_location.get("city") and buyer_location.get("country"):
            client_location_str = f"{buyer_location['city']}, {buyer_location['country']}"
        elif buyer_location.get("country"):
            client_location_str = buyer_location['country']
        
        # Format posted time
        posted_on = opening.get("postedOn", "")
        if posted_on:
            try:
                posted_date = datetime.fromisoformat(posted_on.replace('Z', '+00:00'))
                posted_time = posted_date.strftime("%Y-%m-%d %H:%M UTC")
            except:
                posted_time = posted_on
        else:
            posted_time = "Unknown"
        
        job_details = {
            "id": info.get("id"),
            "ciphertext": info.get("ciphertext"),
            "title": info.get("title"),
            "description": opening.get("description"),
            "status": opening.get("status"),
            "posted_on": posted_time,
            "publish_time": opening.get("publishTime"),
            "workload": opening.get("workload"),
            "contractor_tier": opening.get("contractorTier"),
            "job_type": info.get("type"),
            "budget": budget_display,
            "budget_amount": budget_amount,
            "hourly_budget_min": hourly_min,
            "hourly_budget_max": hourly_max,
            "budget_type": extended_budget.get("hourlyBudgetType"),
            "currency_code": budget_info.get("currencyCode"),
            "engagement_duration": engagement_duration.get("label"),
            "engagement_weeks": engagement_duration.get("weeks"),
            "deliverables": opening.get("deliverables"),
            "deadline": opening.get("deadline"),
            "category": category.get("name"),
            "category_group": category_group.get("name"),
            "skills": skills,
            "total_applicants": client_activity.get("totalApplicants"),
            "total_hired": client_activity.get("totalHired"),
            "total_interviewed": client_activity.get("totalInvitedToInterview"),
            "positions_to_hire": client_activity.get("numberOfPositionsToHire"),
            "client_location": client_location_str,
            "client_country": buyer_location.get("country"),
            "client_timezone": buyer_location.get("countryTimezone"),
            "client_total_assignments": buyer_stats.get("totalAssignments"),
            "client_active_assignments": buyer_stats.get("activeAssignmentsCount"),
            "client_hours": buyer_stats.get("hoursCount"),
            "client_feedback_count": buyer_stats.get("feedbackCount"),
            "client_rating": buyer_stats.get("score"),
            "client_total_jobs": buyer_stats.get("totalJobsWithHires"),
            "client_total_spent": client_total_spent_value,
            "client_open_jobs": buyer_jobs.get("openCount"),
            "client_industry": buyer_company.get("profile", {}).get("industry") if buyer_company.get("profile") else None,
            "client_company_size": buyer_company.get("profile", {}).get("size") if buyer_company.get("profile") else None,
            "payment_verified": buyer_extra.get("isPaymentMethodVerified"),
            "min_job_success_score": qualifications.get("minJobSuccessScore"),
            "min_hours": qualifications.get("minOdeskHours"),
            "min_hours_week": qualifications.get("minHoursWeek"),
            "english_requirement": qualifications.get("prefEnglishSkill"),
            "rising_talent": qualifications.get("risingTalent"),
            "portfolio_required": qualifications.get("shouldHavePortfolio"),
            "tools": [tool.get("name", "") for tool in opening.get("tools", [])],
            "similar_jobs_count": len(similar_jobs) if similar_jobs else None,
            "annotations": opening.get("annotations"),
            "segmentation_data": opening.get("segmentationData"),
            "qualifications": qualifications,
            "similar_jobs": similar_jobs[:5] if similar_jobs else []
        }
        
        return job_details
        
    except Exception as e:
        print(f"[Job Details] ❌ Error extracting job details: {e}")
        import traceback
        traceback.print_exc()
        return {
            "id": data.get("data", {}).get("id") or data.get("id", ""),
            "title": data.get("data", {}).get("title") or data.get("title", "No title"),
            "description": f"Error: {e}"
        }
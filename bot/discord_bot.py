# --- ADVANCED JOB SEARCH RUNNER ---
import asyncio
import os
from datetime import datetime, timezone, timedelta

# ── MERIDIAN imports (lazy-safe — only runs after bot is ready) ──
try:
    import sys as _sys, os as _os
    _sys.path.insert(0, _os.path.dirname(_os.path.dirname(__file__)))
    import config as _meridian_config
    import meridian as _meridian
    from meridian import cost_tracker as _cost_tracker
    _MERIDIAN_AVAILABLE = True
except Exception as _me:
    print(f"[MERIDIAN] Import failed (disabled): {_me}")
    _MERIDIAN_AVAILABLE = False

# ── Discord notifier import (for #meridian-alerts channel) ──
try:
    from bot.discord_notifier import (
        set_bot as _dn_set_bot,
        send_meridian_discord as _dn_send_meridian,
        send_cost_report_discord as _dn_send_cost_report,
    )
    _DISCORD_NOTIFIER_AVAILABLE = True
except Exception as _dne:
    print(f"[DISCORD-NOTIFIER] Import failed (disabled): {_dne}")
    _DISCORD_NOTIFIER_AVAILABLE = False


async def _save_meridian_result(job_id: str, result: dict):
    """Persist MERIDIAN score to the jobs table (best-effort)."""
    try:
        import datetime as _dt
        from db.database import SessionLocal
        from db.models import Job
        with SessionLocal() as s:
            row = s.query(Job).filter(Job.job_id == str(job_id)).first()
            if row:
                row.meridian_score     = result.get("total_score")
                row.meridian_verdict   = result.get("verdict")
                row.meridian_reasoning = result.get("reasoning")
                row.meridian_run_at    = _dt.datetime.utcnow()
                s.commit()
    except Exception as e:
        print(f"[MERIDIAN] DB save error: {e}")


def _save_job_to_db(job: dict) -> int:
    """
    Upsert a job into the DB and assign the next sequential job_number if new.
    Returns the job_number assigned (existing or new), or -1 on failure.
    """
    try:
        from db.database import SessionLocal
        from db.models import Job
        job_id = str(job.get("id") or job.get("ciphertext") or "")
        if not job_id:
            return -1

        # Parse budget to float
        budget_raw = job.get("budget")
        budget_float = None
        if budget_raw:
            try:
                budget_float = float(str(budget_raw).replace("$", "").replace(",", "").split()[0])
            except Exception:
                pass

        with SessionLocal() as s:
            existing = s.query(Job).filter(Job.job_id == job_id).first()
            if existing:
                if existing.job_number:
                    return existing.job_number
                # Row exists but job_number was never assigned — assign one now
                from sqlalchemy import func
                max_num = s.query(func.max(Job.job_number)).scalar() or 0
                existing.job_number = max_num + 1
                s.commit()
                print(f"[DB] Backfilled job_number #{existing.job_number} for existing job: {existing.title[:50]}")
                return existing.job_number

            # Assign the next job_number atomically
            from sqlalchemy import func
            max_num = s.query(func.max(Job.job_number)).scalar() or 0
            new_num = max_num + 1

            row = Job(
                job_id      = job_id,
                job_number  = new_num,
                title       = (job.get("title") or "")[:500],
                description = job.get("description") or "",
                budget      = budget_float,
                skills      = str(job.get("skills") or ""),
                client      = str(job.get("client") or ""),
                job_type    = job.get("job_type") or job.get("engagement") or None,
            )
            s.add(row)
            s.commit()
            print(f"[DB] Saved job #{new_num}: {row.title[:50]}")
            return new_num
    except Exception as e:
        if "duplicate" in str(e).lower() or "unique" in str(e).lower():
            return -1  # already exists, not a real error
        print(f"[DB] Error saving job: {e}")
        return -1


def _store_discord_message_id(job_id: str, discord_message_id: str):
    """Write the Discord message ID back to the jobs row (best-effort, sync)."""
    try:
        from db.database import SessionLocal
        from db.models import Job
        with SessionLocal() as s:
            row = s.query(Job).filter(Job.job_id == str(job_id)).first()
            if row and not row.discord_message_id:
                row.discord_message_id = str(discord_message_id)
                s.commit()
    except Exception as e:
        print(f"[DB] Error storing discord_message_id: {e}")


def _get_relevant_past_jobs(category: str, skills: list) -> list:
    """
    Sync: query PastJob table for the given category, score by skill overlap,
    return top-2 matches as dicts {title, skills, reference_url}.
    Called via run_in_executor so it never blocks the event loop.
    """
    try:
        import json as _json
        from db.database import SessionLocal
        from db.models import PastJob
        with SessionLocal() as s:
            past = (
                s.query(PastJob)
                .filter(PastJob.category == category)
                .order_by(PastJob.weight.desc())
                .all()
            )
    except Exception as e:
        print(f"[PastJobs] DB error: {e}")
        return []

    if not past:
        return []

    # Score each entry by skill overlap with the incoming job
    incoming_skills = {sk.lower() for sk in (skills or [])}
    scored = []
    for p in past:
        try:
            pskills = _json.loads(p.skills) if p.skills else []
        except Exception:
            pskills = []
        overlap = len(incoming_skills & {s.lower() for s in pskills})
        scored.append((overlap, p))

    scored.sort(key=lambda x: x[0], reverse=True)
    results = []
    for _, p in scored[:2]:
        try:
            pskills = _json.loads(p.skills) if p.skills else []
        except Exception:
            pskills = []
        results.append({
            "title":         p.title,
            "skills":        pskills,
            "reference_url": p.reference_url,
        })
    return results


async def _fetch_relevant_past_jobs(category: str, skills: list) -> list:
    """Async wrapper — runs the sync DB query in a thread-pool executor."""
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(
        None, _get_relevant_past_jobs, category, skills
    )


async def fetch_and_build_job_message(job, search_context="", category=""):
    """
    Fetch job details and build a complete message with all information.
    Returns the complete message string or None if auth fails.
    """
    job_id = job.get('id') or job.get('ciphertext')
    job_url = build_job_url(job_id)
    skills = job.get('skills', [])
    
    # Get formatted posting time for display
    posted_time = format_posted_time(job.get('createdDateTime'))
    
    # Build basic job message with REAL-TIME indicator
    # Use a proper UTC, timezone-aware detection timestamp
    detected_utc = datetime.now(timezone.utc)
    detected_time_str = detected_utc.strftime('%H:%M')
    # Discord hard limit is 2000 chars per message.
    # Keep description to 800 chars max so the rest of the message fits.
    # The FULL description is always stored in the database.
    DISCORD_DESC_LIMIT = 800
    raw_desc = job.get('description') or ''
    discord_desc = raw_desc[:DISCORD_DESC_LIMIT] + ('...' if len(raw_desc) > DISCORD_DESC_LIMIT else '')

    job_msg = (
        f"🚨** JOB ALERT** \n"
        f"**{job['title']}** \n"
        f"{discord_desc}\n"
        f"\n"
        f"**Budget:** {job.get('budget', 'N/A')}\n"
        f"**Posted on Upwork**: {posted_time} \n"
        f"**Detected at:** {detected_time_str} UTC\n"
    )
    # Skills — show up to 15 tags, remainder shown as count
    if skills:
        skill_display = ' • '.join(skills[:15])
        if len(skills) > 15:
            skill_display += f' • +{len(skills) - 15} more'
        job_msg += f"**Key Skills:** `{skill_display}`\n"
    job_msg += (
        f"[Open Job]({job_url})\n"
        f"**Found by keyword:** `{search_context}` \n"
    )
    
    # FETCH JOB DETAILS (single attempt, short timeout — visitor API often lacks permissions)
    job_details_response = None
    if job_id:
        try:
            job_details_response = await asyncio.wait_for(
                scraper.fetch_job_details(job_id, max_retries=1),
                timeout=10
            )
            
            if job_details_response and isinstance(job_details_response, dict):
                print(f"[Real-time] ✅ Job details fetched for '{job.get('title', '?')[:40]}'")
            else:
                pass  # Will post with basic info
                
        except (asyncio.TimeoutError, Exception):
            pass  # Will post with basic info

    # ADD DETAILED INFORMATION TO THE MESSAGE (if available)
    if job_details_response and isinstance(job_details_response, dict):
        job_msg += "\n\n**📋 DETAILED JOB INFORMATION:**\n"
        
        job_msg += "```"
        # Job Type
        if job_details_response.get('job_type'):
            job_msg += f"\nJob Type: {job_details_response['job_type']}"

        # Experience Level (fallbacks to original job dict if needed)
        experience_level = (
            job_details_response.get('experience_level')
            or job.get('experience_level')
        )
        if experience_level:
            # Ensure consistent capitalization
            exp_display = str(experience_level).title()
            job_msg += f"\nExperience Level: {exp_display}"

        # Estimated / Engagement Duration
        estimated_duration = (
            job_details_response.get('engagement_duration')
            or job_details_response.get('estimated_duration')
            or job.get('duration_label')
        )
        if estimated_duration:
            job_msg += f"\nEstimated Duration: {estimated_duration}"

        # Weekly Hours (workload / hours per week)
        weekly_hours = (
            job_details_response.get('workload')
            or job_details_response.get('hours_per_week')
            or job.get('workload')
            or job.get('hours_per_week')
        )
        if weekly_hours:
            job_msg += f"\nWeekly Hours: {weekly_hours}"

        # Proposals formatting
        raw_proposals = (
            job_details_response.get('proposals')
            or job.get('proposals')
        )
        if raw_proposals is not None and raw_proposals != "":
            proposals_display = None
            try:
                # If it's numeric try to map to ranges
                if isinstance(raw_proposals, (int, float)) or str(raw_proposals).isdigit():
                    p = int(raw_proposals)
                    if p < 5:
                        proposals_display = "Less than 5"
                    elif p < 10:
                        proposals_display = "5 to 10"
                    elif p < 15:
                        proposals_display = "10 to 15"
                    elif p < 20:
                        proposals_display = "15 to 20"
                    else:
                        proposals_display = "20+"
                else:
                    # If already a descriptive string, just use it
                    proposals_display = str(raw_proposals)
            except Exception:
                proposals_display = str(raw_proposals)
            if proposals_display:
                job_msg += f"\nProposals: {proposals_display}"
        job_msg += "\n```\n"
        job_msg += "+++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++\n"

    return job_msg


async def process_single_search(search):
    """
    Process a single job search - MODIFIED FOR REAL-TIME DETECTION
    Posts ALL new jobs that haven't been seen before, regardless of posting time
    """
    try:
        channel = bot.get_channel(search["channel_id"])
        if channel is None:
            print(f"[Real-time] Channel not found for {search['category']} - {search['keyword']} (ID: {search['channel_id']})")
            return
        
        print(f"[Real-time] Checking for new jobs: {search['keyword']} in category: {search['category']}")
        
        # Get filters from search configuration, use defaults if not provided
        filters = search.get("filters", {
            "contractor_tier": ["2", "3"],  # Intermediate and Expert
            "payment_verified": True,
            "job_type": ["hourly", "fixed"]
        })
        
        # Fetch jobs for this specific keyword with filters
        jobs = await scraper.fetch_jobs(query=search["query"], limit=10, delay=True, filters=filters)
        
        if not jobs:
            print(f"[Real-time] No jobs returned for '{search['keyword']}'")
            return

        # Post jobs that are NEW (not seen before) AND posted within the last 5 minutes
        new_jobs = []
        for job in jobs:
            job_id = job.get('id')
            
            # Skip if we've already posted this job
            if job_id and job_id in sent_job_ids:
                continue
            
            # Mark as seen regardless (so we don't re-check old jobs next cycle)
            if job_id:
                sent_job_ids.add(job_id)
            
            # Only post if posted within the last 5 minutes
            if not is_job_posted_within_minutes(job.get('createdDateTime'), 5):
                continue
            
            # New job posted within 5 minutes
            if job_id:
                new_jobs.append(job)
                print(f"[Real-time] Found new job (< 5 min): '{job.get('title', 'Unknown')[:40]}...'")
        
        if not new_jobs:
            return
        
        print(f"[Real-time] Found {len(new_jobs)} NEW jobs (< 5 min) for keyword: {search['keyword']}")

        # Post new jobs (limit to 3 per search cycle to avoid spam)
        posted_count = 0
        for job in new_jobs[:3]:
            # Save job to DB and get its sequential job_number
            job_id = str(job.get("id") or job.get("ciphertext") or "")
            job_number = _save_job_to_db(job)

            # BUILD COMPLETE MESSAGE WITH ALL DETAILS
            complete_message = await fetch_and_build_job_message(job, f"{search['keyword']}", category=search.get("category", ""))
            
            # Skip if auth failed
            if complete_message is None:
                print(f"[Real-time] Skipping job due to auth failure")
                continue

            # Prepend the job number badge so users can reference it in WhatsApp
            if job_number and job_number not in (-1, 0):
                complete_message = f"🔢 **Job #{job_number}**\n" + complete_message
            
            # POST COMPLETE MESSAGE TO DISCORD
            try:
                sent_msg = await channel.send(complete_message)
                posted_count += 1
                print(f"[Real-time] Posted NEW job #{job_number}: {job.get('title', 'Unknown')[:50]}...")

                # Store Discord message ID so Module 3 can reply to this post later
                if job_id and sent_msg:
                    _store_discord_message_id(job_id, str(sent_msg.id))

                # ── MERIDIAN GATE (after Discord post — never blocks it) ──
                if _MERIDIAN_AVAILABLE and _meridian_config.MERIDIAN_ENABLED and getattr(_meridian_config, "MERIDIAN_DISCORD_CHANNEL_ID", 0):
                    try:
                        meridian_result = await _meridian.run_meridian(job, search["category"])
                        score   = meridian_result.get("total_score", -1)
                        verdict = meridian_result.get("verdict", "pass")
                        cost_pkr = meridian_result.get("_cost_pkr", 0.0)

                        asyncio.create_task(_save_meridian_result(job.get("id"), meridian_result))
                        print(f"[MERIDIAN] '{job.get('title','?')[:40]}' → {score}/100 ({verdict.upper()}) ₨{cost_pkr:.4f}")

                        # ── MERIDIAN → #meridian-alerts Discord channel ──
                        # Fires for BOTH pass and skip verdicts (fire-and-forget)
                        if _DISCORD_NOTIFIER_AVAILABLE:
                            _resolved_job_number = job_number if (job_number and job_number not in (-1, 0)) else 0
                            # Fetch past job matches for this category to show in the MERIDIAN alert
                            _past_matches = await _fetch_relevant_past_jobs(search["category"], job.get("skills", []))
                            asyncio.create_task(
                                _dn_send_meridian(
                                    job, meridian_result, search["category"],
                                    cost_pkr=cost_pkr,
                                    job_number=_resolved_job_number,
                                    verdict=verdict,
                                    past_matches=_past_matches,
                                )
                            )
                    except Exception as _me:
                        print(f"[MERIDIAN] Gate error (non-fatal): {_me}")

                await asyncio.sleep(2)  # Rate limit protection
            except Exception as post_error:
                print(f"[Real-time] Error posting message: {post_error}")
            
        if posted_count > 0:
            print(f"[Real-time] Posted {posted_count} new jobs for: {search['keyword']}")
            
    except Exception as e:
        error_msg = f"Error in real-time job detection for **{search['keyword']}**: {e}"
        try:
            channel = bot.get_channel(search["channel_id"])
            if channel:
                await channel.send(error_msg)
        except:
            pass
        print(f"[Real-time] Error in {search['keyword']}: {e}")


async def run_advanced_job_searches():
    """
    Run job searches in small batches to balance speed vs rate-limiting.
    Processes 5 keywords concurrently per batch, with a short pause between batches.
    Skip any search entry with enabled=False.
    """
    await bot.wait_until_ready()
    # Filter out disabled entries (enabled=False); default is enabled when key is absent
    active_searches = [s for s in ADVANCED_JOB_SEARCHES if s.get("enabled", True)]
    disabled_count  = len(ADVANCED_JOB_SEARCHES) - len(active_searches)
    if disabled_count:
        print(f"[Real-time] {disabled_count} keyword(s) disabled (enabled=False) — skipping them")
    print(f"[Real-time] Starting job monitoring cycle ({len(active_searches)} active keywords)...")
    
    success_count = 0
    error_count = 0
    batch_size = 5
    
    for batch_start in range(0, len(active_searches), batch_size):
        batch = active_searches[batch_start:batch_start + batch_size]
        batch_num = (batch_start // batch_size) + 1
        
        # Run batch concurrently
        tasks = [asyncio.create_task(process_single_search(s)) for s in batch]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        for j, result in enumerate(results):
            if isinstance(result, Exception):
                error_count += 1
                err_str = str(result)
                kw = batch[j]['keyword']
                if '429' in err_str:
                    print(f"[Real-time] Rate-limited on '{kw}', backing off")
                    await asyncio.sleep(15)
                else:
                    print(f"[Real-time] Error in '{kw}': {result}")
            else:
                success_count += 1
        
        # Brief pause between batches to avoid rate limits
        if batch_start + batch_size < len(active_searches):
            await asyncio.sleep(random.uniform(3, 5))
    
    print(f"[Real-time] Completed scan: {success_count} OK, {error_count} errors")

    # ── MERIDIAN CYCLE FINANCE REPORT ───────────────────────────
    if _MERIDIAN_AVAILABLE and _meridian_config.MERIDIAN_ENABLED and getattr(_meridian_config, "MERIDIAN_DISCORD_CHANNEL_ID", 0):
        try:
            report = _cost_tracker.flush_cycle_report()
            if report and _DISCORD_NOTIFIER_AVAILABLE:
                asyncio.create_task(_dn_send_cost_report(report))
        except Exception as _fe:
            print(f"[MERIDIAN] Finance report error: {_fe}")

import discord
from discord.ext import commands, tasks
from scraper.upwork_scraper import UpworkScraper
from scraper.bhw_scraper import post_new_bhw_threads
from config import DISCORD_TOKEN, DISCORD_CHANNEL_ID, UPWORK_EMAIL, UPWORK_PASSWORD,DISCORD_CHANNEL_ID2
import asyncio
import re
import random

from datetime import datetime
import traceback

# --- ADVANCED JOB SEARCH KEYWORDS AND CHANNELS ---
# Map: (keyword_name, search_query, channel_id)
from .job_search_keywords import ADVANCED_JOB_SEARCHES

# Only request the intents this bot actually needs.
# The message-reading commands are all commented out, so no privileged intents
# (Members / Message Content) are required — default is enough.
_intents = discord.Intents.default()
_intents.message_content = False   # not reading user messages (message_content is privileged)
bot = commands.Bot(command_prefix="!", intents=_intents)
scraper = UpworkScraper()

# --- UNIQUE JOBS TRACKER ---
sent_job_ids = set()

# Store the last search time to prevent spam
last_search_time = {}
COOLDOWN_SECONDS = 30  # Prevent searches more than once every 30 seconds per user

def build_job_url(job_id):
    """Builds the correct Upwork job URL with modal info."""
    if not job_id:
        return None
    
    job_id = str(job_id)
    
    # FIXED: Remove any existing ~ prefix first, then add one
    clean_job_id = job_id.lstrip("~")
    
    # Don't add double ~ prefix
    return f"https://www.upwork.com/freelance-jobs/apply/~{clean_job_id}"

def build_job_details_embed(job_details):
    """Build a comprehensive detailed embed with horizontal layout matching Upwork job details"""
    if not job_details:
        return discord.Embed(
            title="❌ Job Details Unavailable",
            description="Unable to fetch detailed job information at this time.",
            color=0xe74c3c
        )
    
    # Create main title and description
    # Embed description cap: 4096 chars (Discord limit), use 800 for readability
    title = f"📋 {job_details.get('title', 'Job Details')}"
    _raw_desc = job_details.get('description', 'No description available')
    description = _raw_desc[:800] + ('...' if len(_raw_desc) > 800 else '')
    
    # Build embed with each field as inline and a gap between fields
    embed = discord.Embed(
        title=title,
        description=description,
        color=0x2ecc71,
        url=build_job_url(job_details.get('ciphertext') or job_details.get('id'))
    )

    # Add job overview fields
    if job_details.get('budget'):
        embed.add_field(name="💰 Budget", value=job_details['budget'], inline=True)
    # if job_details.get('contractor_tier'):
    #     embed.add_field(name="📊 Contractor Tier", value=job_details['contractor_tier'], inline=True)
    embed.add_field(name="", value="", inline=False)  # gap

    # Project details
    if job_details.get('job_type'):
        embed.add_field(name="💼 Job Type", value=job_details['job_type'], inline=True)
    if job_details.get('engagement_duration'):
        embed.add_field(name="⏳ Engagement Duration", value=job_details['engagement_duration'], inline=True)
    # if job_details.get('workload'):
    #     embed.add_field(name="⏱️ Workload", value=job_details['workload'], inline=True)
    # if job_details.get('deadline'):
    #     embed.add_field(name="📅 Deadline", value=job_details['deadline'], inline=True)

    embed.add_field(name="", value="", inline=False)

    # Activity on this job
    # embed.add_field(name="📝 Proposals", value=job_details.get('total_applicants', 0), inline=True)
    # embed.add_field(name="💬 Interviewing", value=job_details.get('total_interviewed', 0), inline=True)
    # embed.add_field(name="✅ Hired", value=job_details.get('total_hired', 0), inline=True)
    # embed.add_field(name="👤 Positions", value=job_details.get('positions_to_hire', 1), inline=True)

    embed.add_field(name="", value="", inline=False)

    # Client fields removed — all client info (location, spent, payment_verified)
    # requires OAuth2 (jobPubDetails returns ExecutionAborted for visitor tokens)

    embed.add_field(name="", value="", inline=False)

    # Requirements
    if job_details.get('min_job_success_score'):
        embed.add_field(name="⭐ Min Success Score", value=f"{job_details['min_job_success_score']}%", inline=True)
    if job_details.get('min_hours'):
        embed.add_field(name="🕐 Min Platform Hours", value=job_details['min_hours'], inline=True)
    if job_details.get('min_hours_week'):
        embed.add_field(name="📅 Min Hours/Week", value=job_details['min_hours_week'], inline=True)
    if job_details.get('portfolio_required', False):
        embed.add_field(name="📁 Portfolio Required", value="Yes", inline=True)
    if job_details.get('rising_talent', False):
        embed.add_field(name="🌟 Rising Talent Welcome", value="Yes", inline=True)
    if job_details.get('english_requirement', 'ANY') != 'ANY':
        embed.add_field(name="🗣️ English", value=job_details['english_requirement'], inline=True)

    embed.add_field(name="", value="", inline=False)

    # Tools
    tools = job_details.get('tools', [])
    # if tools:
    #     tools_display = ' • '.join(tools[:15])
    #     if len(tools) > 15:
    #         tools_display += f" • +{len(tools) - 15} more"
    #     embed.add_field(name=f"🛠️ Tools ({len(tools)})", value=tools_display, inline=True)

    # Additional info
    additional_parts = []
    if job_details.get('deliverables'):
        deliverables = job_details['deliverables'][:100]
        if len(job_details['deliverables']) > 100:
            deliverables += "..."
        additional_parts.append(f"📦 {deliverables}")
    if job_details.get('category'):
        additional_parts.append(f"📂 {job_details['category']}")
    similar_jobs_count = job_details.get('similar_jobs_count')
    if similar_jobs_count:
        additional_parts.append(f"🔗 {similar_jobs_count} similar jobs available")
    # if additional_parts:
    #     embed.add_field(name="ℹ️ Additional Info", value='\n'.join(additional_parts), inline=True)

    # Enhanced footer with posting and status info
    footer_parts = []
    if job_details.get('posted_on'):
        footer_parts.append(f"📅 Posted: {format_posted_time(job_details['posted_on'])}")
    if job_details.get('status'):
        footer_parts.append(f"Status: {job_details['status']}")
    if job_details.get('publish_time'):
        footer_parts.append(f"Published: {format_posted_time(job_details['publish_time'])}")

    footer_text = " • ".join(footer_parts) if footer_parts else "Comprehensive Job Details"
    embed.set_footer(
        text=footer_text,
        icon_url="https://img.icons8.com/fluency/48/000000/upwork.png"
    )

    return embed

def is_job_posted_within_minutes(created_datetime, minutes=5):
    """Check if job was posted within the specified number of minutes."""
    from datetime import datetime, timezone
    if not created_datetime or created_datetime == 'Unknown':
        return False
    
    now = datetime.now(timezone.utc)
    dt = None
    
    try:
        # If it's a datetime object
        if hasattr(created_datetime, 'strftime'):
            dt = created_datetime
            if not hasattr(dt, 'tzinfo') or dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
        # If it's a timestamp (int or float)
        elif isinstance(created_datetime, (int, float)):
            dt = datetime.utcfromtimestamp(created_datetime).replace(tzinfo=timezone.utc)
        # If it's a string
        elif isinstance(created_datetime, str):
            # Try ISO format
            try:
                dt = datetime.fromisoformat(created_datetime.replace('Z', '+00:00'))
                if not hasattr(dt, 'tzinfo') or dt.tzinfo is None:
                    dt = dt.replace(tzinfo=timezone.utc)
            except Exception:
                pass
            if dt is None:
                # Try parsing as float timestamp string
                try:
                    ts = float(created_datetime)
                    dt = datetime.utcfromtimestamp(ts).replace(tzinfo=timezone.utc)
                except Exception:
                    pass
        
        if dt is None:
            return False
        
        # Calculate time difference
        diff = now - dt
        minutes_ago = diff.total_seconds() / 60
        return minutes_ago <= minutes
        
    except Exception:
        return False

def format_posted_time(created_datetime):
    """Format the posting time as 'X mins ago', 'Y secs ago', etc."""
    import time
    from datetime import datetime, timezone
    if not created_datetime or created_datetime == 'Unknown':
        return "Unknown"

    now = datetime.now(timezone.utc)
    dt = None
    try:
        # If it's a datetime object
        if hasattr(created_datetime, 'strftime'):
            dt = created_datetime
            if not hasattr(dt, 'tzinfo') or dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
        # If it's a timestamp (int or float)
        elif isinstance(created_datetime, (int, float)):
            dt = datetime.utcfromtimestamp(created_datetime).replace(tzinfo=timezone.utc)
        # If it's a string
        elif isinstance(created_datetime, str):
            # Try ISO format
            try:
                dt = datetime.fromisoformat(created_datetime.replace('Z', '+00:00'))
                if not hasattr(dt, 'tzinfo') or dt.tzinfo is None:
                    dt = dt.replace(tzinfo=timezone.utc)
            except Exception:
                pass
            if dt is None:
                # Try parsing as float timestamp string
                try:
                    ts = float(created_datetime)
                    dt = datetime.utcfromtimestamp(ts).replace(tzinfo=timezone.utc)
                except Exception:
                    pass
        if dt is None:
            return str(created_datetime)[:10] if len(str(created_datetime)) > 10 else str(created_datetime)

        # Calculate time difference
        diff = now - dt
        seconds = int(diff.total_seconds())
        if seconds < 0:
            seconds = 0
        if seconds < 60:
            return f"{seconds} sec{'s' if seconds != 1 else ''} ago"
        minutes = seconds // 60
        if minutes < 60:
            return f"{minutes} min{'s' if minutes != 1 else ''} ago"
        hours = minutes // 60
        if hours < 24:
            return f"{hours} hour{'s' if hours != 1 else ''} ago"
        days = hours // 24
        if days < 7:
            return f"{days} day{'s' if days != 1 else ''} ago"
        weeks = days // 7
        if weeks < 4:
            return f"{weeks} week{'s' if weeks != 1 else ''} ago"
        months = days // 30
        if months < 12:
            return f"{months} month{'s' if months != 1 else ''} ago"
        years = days // 365
        return f"{years} year{'s' if years != 1 else ''} ago"
    except Exception:
        return "Unknown"

# ADD DEBUG FUNCTION
def debug_job_ids(jobs_data):
    """Debug function to check job IDs"""
    print("\n=== JOB ID DEBUG ===")
    for i, job in enumerate(jobs_data[:3]):  # Check first 3 jobs
        job_id = job.get('id')
        print(f"Job {i+1}:")
        print(f"  ID: {job_id}")
        print(f"  Title: {job.get('title', 'No title')[:50]}...")
        print(f"  ID starts with ~: {str(job_id).startswith('~') if job_id else False}")
        print(f"  ID length: {len(str(job_id)) if job_id else 0}")
        
        # Test URL generation
        test_url = build_job_url(job_id)
        print(f"  Generated URL: {test_url}")
        print()
    print("===================\n")

@bot.event
async def on_ready():
    print(f"Bot is ready. Username: {bot.user}")
    # Inject bot reference into Discord notifier so it can reach #meridian-alerts
    if _DISCORD_NOTIFIER_AVAILABLE:
        _dn_set_bot(bot)
        ch_id = getattr(_meridian_config, "MERIDIAN_DISCORD_CHANNEL_ID", 0) if _MERIDIAN_AVAILABLE else 0
        if ch_id:
            print(f"[DISCORD-NOTIFIER] MERIDIAN alerts → channel #{ch_id}")
        else:
            print("[DISCORD-NOTIFIER] MERIDIAN_DISCORD_CHANNEL_ID not set — Discord alerts disabled")
    # Sync slash commands globally
    try:
        synced = await bot.tree.sync()
        print(f"[SLASH] Synced {len(synced)} slash command(s)")
    except Exception as _se:
        print(f"[SLASH] Sync error: {_se}")
    bot.loop.create_task(run_scrapers_concurrently())
    bot.loop.create_task(_start_draft_http_server())


@bot.tree.command(name="agree", description="Generate a proposal draft for a job. Usage: /agree <job_number>")
@discord.app_commands.describe(job_number="The job number shown in the job alert (e.g. 7)")
async def agree_slash(interaction: discord.Interaction, job_number: int):
    """Slash command: /agree <job_number> — triggers proposal draft generation."""
    meridian_ch_id = getattr(_meridian_config, "MERIDIAN_DISCORD_CHANNEL_ID", 0) if _MERIDIAN_AVAILABLE else 0
    if meridian_ch_id and interaction.channel_id != int(meridian_ch_id):
        await interaction.response.send_message("Use this command in #meridian-alerts.", ephemeral=True)
        return
    if job_number < 1:
        await interaction.response.send_message("Job number must be a positive integer.", ephemeral=True)
        return
    await interaction.response.send_message(f"Got it — generating proposal draft for Job #{job_number}...")
    asyncio.create_task(_generate_and_deliver_draft(job_number))


# ── Module 3: Draft HTTP server ───────────────────────────────────────────────
# Fallback entry point — accepts POST /draft  body: {"job_number": <int>}
# Primary trigger is the /agree slash command above.

DRAFT_SERVER_PORT = 8765


async def _handle_draft_request(reader, writer):
    """
    Minimal async HTTP handler.
    Accepts: POST /draft  body: {"job_number": <int>}
    """
    try:
        import json as _json
        raw = await asyncio.wait_for(reader.read(4096), timeout=5)
        raw_str = raw.decode("utf-8", errors="ignore")

        # Parse body JSON (skip HTTP headers, grab last non-empty line)
        body_str = ""
        parts = raw_str.split("\r\n\r\n", 1)
        if len(parts) == 2:
            body_str = parts[1].strip()
        if not body_str:
            body_str = raw_str.strip().split("\n")[-1].strip()

        try:
            payload = _json.loads(body_str)
        except Exception:
            writer.write(b"HTTP/1.1 400 Bad Request\r\n\r\n{\"error\":\"invalid json\"}")
            await writer.drain()
            writer.close()
            return

        job_number = payload.get("job_number")
        if not isinstance(job_number, int) or job_number < 1:
            writer.write(b"HTTP/1.1 400 Bad Request\r\n\r\n{\"error\":\"job_number must be a positive int\"}")
            await writer.drain()
            writer.close()
            return

        print(f"[PROPOSALS] Draft requested for job #{job_number}")

        # Respond 202 immediately so the bridge doesn't time out
        writer.write(b"HTTP/1.1 202 Accepted\r\nContent-Type: application/json\r\n\r\n{\"status\":\"generating\"}")
        await writer.drain()
        writer.close()

        # Generate and deliver draft asynchronously
        asyncio.create_task(_generate_and_deliver_draft(job_number))

    except Exception as e:
        print(f"[PROPOSALS] HTTP handler error: {e}")
        try:
            writer.write(b"HTTP/1.1 500 Internal Server Error\r\n\r\n")
            await writer.drain()
            writer.close()
        except Exception:
            pass


async def _generate_and_deliver_draft(job_number: int):
    """Generate a proposal draft and deliver it to #meridian-alerts Discord."""
    try:
        from proposals.generator import generate_proposal
        from bot.discord_notifier import send_proposal_discord as _dn_send_proposal

        result = await generate_proposal(job_number)

        # Deliver to #meridian-alerts Discord channel
        try:
            await _dn_send_proposal(result)
        except Exception as _de:
            print(f"[PROPOSALS] Discord delivery error (non-fatal): {_de}")

        if result.get("ok"):
            print(f"[PROPOSALS] Draft for job #{job_number} delivered ✅")
        else:
            print(f"[PROPOSALS] Draft for job #{job_number} failed: {result.get('error')}")
    except Exception as e:
        print(f"[PROPOSALS] Unexpected error for job #{job_number}: {e}")


async def _start_draft_http_server():
    """Start the draft HTTP server on DRAFT_SERVER_PORT."""
    await bot.wait_until_ready()
    try:
        server = await asyncio.start_server(
            _handle_draft_request,
            host="127.0.0.1",
            port=DRAFT_SERVER_PORT,
        )
        print(f"[PROPOSALS] Draft server listening on 127.0.0.1:{DRAFT_SERVER_PORT}")
        async with server:
            await server.serve_forever()
    except Exception as e:
        print(f"[PROPOSALS] Could not start draft server: {e}")

# @bot.event
# async def on_message(message):
#     # Don't respond to bot's own messages
#     if message.author == bot.user:
#         return
    
#     # Only respond in the designated channel
#     if message.channel.id != DISCORD_CHANNEL_ID:
#         return
    
#     # Don't respond to commands (let command handler deal with them)
#     if message.content.startswith(bot.command_prefix):
#         await bot.process_commands(message)
#         return
    
#     # Check cooldown
#     user_id = message.author.id
#     current_time = asyncio.get_event_loop().time()
    
#     if user_id in last_search_time:
#         if current_time - last_search_time[user_id] < COOLDOWN_SECONDS:
#             await message.add_reaction("⏰")  # Clock emoji to indicate cooldown
#             return
    
#     last_search_time[user_id] = current_time
    
#     # Extract keywords from the message
#     keyword = message.content.strip()
    
#     # Skip very short messages or common words
#     if len(keyword) < 2 or keyword.lower() in ['hi', 'hello', 'hey', 'ok', 'yes', 'no', 'thanks']:
#         return
    
#     # Add a loading reaction
#     await message.add_reaction("🔍")
    
#     try:
#         # Search for jobs using the keyword
#         print(f"🔍 Searching for jobs with keyword: '{keyword}'")
#         jobs = await scraper.fetch_jobs(query=keyword, limit=5)
        
#         if jobs:
#             print(f"✅ Found {len(jobs)} jobs for keyword: '{keyword}'")
            
#             # ADD: Debug job IDs
#             debug_job_ids(jobs)
            
#             # Create embed for search results with horizontal layout
#             main_embed = discord.Embed(
#                 title=f"🎯 Search Results: '{keyword}'",
#                 description=f"Found **{len(jobs)}** matching jobs",
#                 color=0x00ff00
#             )
#             main_embed.add_field(name="👤 Requested by", value=message.author.display_name, inline=True)
#             main_embed.add_field(name="📊 Results", value=f"Showing top {min(len(jobs), 3)}", inline=True)
#             main_embed.add_field(name="🕒 Search Time", value=datetime.now().strftime("%H:%M"), inline=True)
#             await message.channel.send(embed=main_embed)

#             # Send individual job embeds with improved horizontal layout (limit to first 3)
#             for i, job in enumerate(jobs[:3], 1):
#                 embed = discord.Embed(
#                     title=f"📋 {job['title']}",
#                     description=job['description'][:400] + "..." if len(job['description']) > 400 else job['description'],
#                     color=0x1abc9c,
#                     url=build_job_url(job.get('id'))
#                 )
                
#                 # ROW 1: Budget, Experience, Type (3 columns)
#                 embed.add_field(name="💰 Budget", value=job.get('budget', 'N/A'), inline=True)
#                 embed.add_field(name="📊 Experience", value=job.get('experience_level', 'Any'), inline=True)
#                 embed.add_field(name="💼 Type", value=job.get('job_type', 'N/A'), inline=True)
                
#                 # ROW 2: Duration, Posted, Apply (3 columns)
#                 embed.add_field(name="⏱️ Duration", value=job.get('duration_label', 'N/A'), inline=True)
#                 embed.add_field(name="🕒 Posted", value=format_posted_time(job.get('createdDateTime')), inline=True)
#                 embed.add_field(name="🌐 Quick Apply", value="[Open Job]("+build_job_url(job.get('id'))+")", inline=True)
                
#                 # Skills row (full width but compact)
#                 skills = job.get('skills', [])
#                 if skills:
#                     skill_display = " • ".join(skills[:10])
#                     if len(skills) > 10:
#                         skill_display += f" • +{len(skills) - 10} more"
#                     embed.add_field(
#                         name="🎯 Required Skills",
#                         value=f"`{skill_display}`",
#                         inline=False
#                     )
                
#                 embed.set_footer(
#                     text=f"Result {i} of {min(len(jobs), 3)} • Detailed info will be posted in thread automatically",
#                     icon_url="https://img.icons8.com/fluency/48/000000/upwork.png"
#                 )
                
#                 # Post job with automatic details in thread
#                 await post_job_with_auto_details(message.channel, job, embed=embed, search_context=f"User search: {keyword}")
#                 await asyncio.sleep(1)
            
#             # If there are more jobs, show summary
#             if len(jobs) > 3:
#                 overflow_embed = discord.Embed(
#                     title="📋 More Results Available",
#                     description=f"Found **{len(jobs) - 3}** additional jobs",
#                     color=0xf39c12
#                 )
#                 overflow_embed.add_field(name="💡 Tip", value=f"Use `!jobs {keyword}` to see all results", inline=True)
#                 overflow_embed.add_field(name="🔍 Refine", value="Try more specific keywords", inline=True)
#                 await message.channel.send(embed=overflow_embed)
            
#             # Remove the loading reaction and add success
#             await message.remove_reaction("🔍", bot.user)
#             await message.add_reaction("✅")
            
#         else:
#             # No jobs found with enhanced layout
#             embed = discord.Embed(
#                 title="😞 No Jobs Found",
#                 description=f"No jobs matching **'{keyword}'** found right now",
#                 color=0xe74c3c
#             )
#             embed.add_field(name="💡 Try These", value="• python\n• web developer\n• data analyst", inline=True)
#             embed.add_field(name="🔄 Or Try", value="• graphic design\n• content writing\n• social media", inline=True)
#             embed.add_field(name="⏰ Check Back", value="New jobs posted hourly!", inline=True)
#             await message.channel.send(embed=embed)
            
#             # Remove loading and add sad reaction
#             await message.remove_reaction("🔍", bot.user)
#             await message.add_reaction("😞")
    
#     except Exception as e:
#         print(f"❌ Error searching for jobs: {e}")
        
#         error_embed = discord.Embed(
#             title="⚠️ Search Error",
#             description="Something went wrong while searching for jobs.",
#             color=0xe74c3c
#         )
#         error_embed.add_field(name="🔧 Status", value="Temporary issue", inline=True)
#         error_embed.add_field(name="⏰ Retry", value="Try again in a moment", inline=True)
#         error_embed.add_field(name="💬 Help", value="Use `!help_jobs` for tips", inline=True)
#         await message.channel.send(embed=error_embed)
        
#         # Remove loading and add error reaction
#         await message.remove_reaction("🔍", bot.user)
#         await message.add_reaction("❌")
    
#     # Process commands after handling the message
#     await bot.process_commands(message)

# @bot.command()
# async def jobs(ctx, *, keyword=None):
#     """Command to search for jobs with enhanced horizontal layout"""
#     if not keyword:
#         msg = (
#             "🔍 **Job Search Command**\n"
#             "Search for Upwork jobs with detailed results\n\n"
#             "📝 **Usage:** `!jobs <keyword>`\n"
#             "💡 **Example:** `!jobs python developer`\n"
#             "📊 **Results:** Shows up to 10 jobs with auto-generated detail threads"
#         )
#         await ctx.send(msg)
#         return

#     # Add loading message
#     loading_msg = await ctx.send("🔍 Searching for jobs...")

#     try:
#         jobs = await scraper.fetch_jobs(query=keyword, limit=10)
#         # Filter jobs by keyword in title, description, or skills
#         keyword_lower = keyword.lower()
#         filtered_jobs = []
#         for job in jobs:
#             title = job.get('title', '').lower()
#             description = job.get('description', '').lower()
#             skills = [s.lower() for s in job.get('skills', [])]
#             if (
#                 keyword_lower in title
#                 or keyword_lower in description
#                 or any(keyword_lower in skill for skill in skills)
#             ):
#                 filtered_jobs.append(job)

#         if filtered_jobs:
#             # Delete loading message
#             await loading_msg.delete()

#             # Create main results message
#             main_msg = (
#                 f"🎯 **Search Results: '{keyword}'**\n"
#                 f"Found **{len(filtered_jobs)}** relevant jobs\n"
#                 f"👤 **Requested by:** {ctx.author.display_name}\n"
#                 f"📊 **Showing:** {min(len(filtered_jobs), 10)} jobs\n"
#                 f"🕒 **Search Time:** {datetime.now().strftime('%H:%M UTC')}\n"
#                 f"📋 **Note:** Detailed info will be automatically posted in threads for each job\n"
#             )
#             await ctx.send(main_msg)

#             # Send all filtered jobs found (up to 10) with auto details
#             for i, job in enumerate(filtered_jobs, 1):
#                 job_url = build_job_url(job.get('id'))
#                 skills = job.get('skills', [])
#                 skill_display = ""
#                 if skills:
#                     skill_display = " • ".join(skills[:12])
#                     if len(skills) > 12:
#                         skill_display += f" • +{len(skills) - 12} more"

#                 job_msg = (
#                     "----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------\n"
#                     f"📋 **{job['title']}**\n"
#                     f"{job['description'][:350] + '...' if len(job['description']) > 350 else job['description']}\n\n"
#                     f"💰 **Budget:** {job.get('budget', 'N/A')}\n"
#                     f"📊 **Level:** {job.get('experience_level', 'Any')}\n"
#                     f"💼 **Type:** {job.get('job_type', 'N/A')}\n"
#                     f"⏱️ **Duration:** {job.get('duration_label', 'N/A')}\n"
#                     f"🕒 **Posted:** {format_posted_time(job.get('createdDateTime'))}\n"
#                     f"🎯 **Result:** #{i} of {len(filtered_jobs)}\n"
#                 )
#                 if skill_display:
#                     job_msg += f"🎯 **Required Skills:** `{skill_display}`\n"
#                 job_msg += (
#                     f"🌐 [Open Job]({job_url})\n"
#                     f"Job {i} of {len(filtered_jobs)} • Detailed info will be posted in thread below.\n"
#                     "---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------\n"
#                 )
                
#                 # Post job with automatic details in thread
#                 await post_job_with_auto_details(ctx.channel, job, job_msg, f"Command search: {keyword}")
#                 await asyncio.sleep(0.5)
#         else:
#             await loading_msg.edit(content="😞 No jobs found for that keyword. Try different search terms!")

#     except Exception as e:
#         print(f"❌ Error in jobs command: {e}")
#         await loading_msg.edit(content="❌ An error occurred while searching. Please try again later.")

# @bot.command()
# async def skills(ctx, *, keyword=None):
#     """Command to search for jobs with enhanced skills analysis and horizontal layout"""
#     if not keyword:
#         embed = discord.Embed(
#             title="🎯 Skills Analysis Command",
#             description="Analyze skills required for specific job types",
#             color=0x3498db
#         )
#         embed.add_field(name="📝 Usage", value="`!skills <keyword>`", inline=True)
#         embed.add_field(name="💡 Example", value="`!skills react developer`", inline=True)
#         embed.add_field(name="📊 Analysis", value="Shows skills breakdown with auto-generated detail threads", inline=True)
#         await ctx.send(embed=embed)
#         return
    
#     # Add loading message
#     loading_msg = await ctx.send("🔍 Searching jobs and analyzing skills...")
    
#     try:
#         jobs = await scraper.fetch_jobs(query=keyword, limit=5)
        
#         if jobs:
#             # Delete loading message
#             await loading_msg.delete()
            
#             # Create skills summary
#             all_skills = {}
#             for job in jobs:
#                 for skill in job.get('skills', []):
#                     if skill and skill.strip():
#                         all_skills[skill] = all_skills.get(skill, 0) + 1
            
#             # Sort skills by frequency
#             sorted_skills = sorted(all_skills.items(), key=lambda x: x[1], reverse=True)
            
#             # Create enhanced skills summary embed
#             skills_embed = discord.Embed(
#                 title=f"🎯 Skills Analysis: '{keyword}'",
#                 description=f"Analyzed **{len(jobs)}** jobs with **{len(all_skills)}** unique skills",
#                 color=0x9b59b6
#             )
            
#             # Stats row (3 columns)
#             skills_embed.add_field(name="📊 Jobs Analyzed", value=str(len(jobs)), inline=True)
#             skills_embed.add_field(name="🎯 Unique Skills", value=str(len(all_skills)), inline=True)
#             skills_embed.add_field(name="🔥 Top Skills", value=str(min(10, len(sorted_skills))), inline=True)
            
#             # Show top 12 most requested skills in compact format
#             if sorted_skills:
#                 top_skills = sorted_skills[:12]
#                 skills_text = " • ".join([f"**{skill}** ({count})" for skill, count in top_skills])
#                 skills_embed.add_field(
#                     name="🔥 Most In-Demand Skills",
#                     value=skills_text,
#                     inline=False
#                 )
            
#             skills_embed.set_footer(text=f"Analysis complete • Requested by {ctx.author.display_name}")
#             await ctx.send(embed=skills_embed)
            
#             # Send individual job embeds with enhanced skills focus and auto details
#             for i, job in enumerate(jobs, 1):
#                 embed = discord.Embed(
#                     title=f"📋 {job['title']}",
#                     description=job['description'][:300] + "..." if len(job['description']) > 300 else job['description'],
#                     color=0x8e44ad,
#                     url=build_job_url(job.get('id'))
#                 )
                
#                 # ROW 1: Budget, Experience, Type (3 columns)
#                 embed.add_field(name="💰 Budget", value=job.get('budget', 'N/A'), inline=True)
#                 embed.add_field(name="📊 Level", value=job.get('experience_level', 'Any'), inline=True)
#                 embed.add_field(name="💼 Type", value=job.get('job_type', 'N/A'), inline=True)
                
#                 # Skills analysis (full width, prominent)
#                 skills = job.get('skills', [])
#                 skills_count = len(skills)
#                 if skills:
#                     skill_display = " • ".join(skills[:10])
#                     if len(skills) > 10:
#                         skill_display += f" • +{len(skills) - 10} more"
#                     embed.add_field(
#                         name=f"🎯 Required Skills ({skills_count} total)",
#                         value=f"`{skill_display}`",
#                         inline=False
#                     )
#                 else:
#                     embed.add_field(
#                         name="🎯 Skills",
#                         value="No specific skills listed",
#                         inline=False
#                     )
                
#                 # ROW 2: Duration, Posted, Skills Count (3 columns)
#                 embed.add_field(name="⏱️ Duration", value=job.get('duration_label', 'N/A'), inline=True)
#                 embed.add_field(name="🕒 Posted", value=format_posted_time(job.get('createdDateTime')), inline=True)
#                 embed.add_field(name="📊 Skills Count", value=f"{skills_count} skills", inline=True)
                
#                 embed.set_footer(
#                     text=f"Skills Analysis {i}/{len(jobs)} • Detailed info will be posted in thread below",
#                     icon_url="https://img.icons8.com/fluency/48/000000/clock.png"
#                 )
                
#                 # Post job with automatic details in thread
#                 await post_job_with_auto_details(ctx.channel, job, embed=embed, search_context=f"Skills analysis: {keyword}")
#                 await asyncio.sleep(0.5)
#         else:
#             await loading_msg.edit(content="😞 No jobs found for skills analysis. Try different search terms!")
            
#     except Exception as e:
#         print(f"❌ Error in skills command: {e}")
#         await loading_msg.edit(content="❌ An error occurred while analyzing skills. Please try again later.")

@bot.command()
async def help_jobs(ctx):
    """Show help for job searching with enhanced horizontal layout"""
    embed = discord.Embed(
        title="🤖 Enhanced Job Bot Help",
        description="Find Upwork jobs with advanced search, auto-generated detailed threads!",
        color=0x3498db
    )
    
    # Features row (3 columns)
    embed.add_field(name="💬 Auto Search", value="Type keywords for instant results", inline=True)
    embed.add_field(name="🔍 Manual Search", value="`!jobs <keyword>` for detailed results", inline=True)
    embed.add_field(name="🎯 Skills Analysis", value="`!skills <keyword>` for skill breakdown", inline=True)
    
    # Commands row (3 columns)
    embed.add_field(name="📝 Basic Search", value="`!jobs python developer`", inline=True)
    embed.add_field(name="🔬 Skills Focus", value="`!skills react developer`", inline=True)
    embed.add_field(name="❓ Get Help", value="`!help_jobs` (this command)", inline=True)
    
    # Auto-thread features (full width)
    embed.add_field(
        name="🧵 Automatic Thread Creation",
        value="**Every job automatically gets a detailed thread** with comprehensive information including client details, requirements, full skill lists, and more. No buttons needed!",
        inline=False
    )
    
    # Settings row (3 columns)
    embed.add_field(name="⏰ Auto-Search Cooldown", value=f"{COOLDOWN_SECONDS} seconds", inline=True)
    embed.add_field(name="📊 Results Per Search", value="Up to 10 jobs", inline=True)
    embed.add_field(name="🔄 Updates", value="Real-time job alerts", inline=True)
    
    # Examples (full width)
    embed.add_field(
        name="💡 Search Examples",
        value="`python` • `web developer` • `data analysis` • `graphic design` • `content writing` • `social media` • `wordpress` • `react developer`",
        inline=False
    )
    
    # New features highlight
    embed.add_field(
        name="🆕 Enhanced Features",
        value="**Auto Thread Details** - Comprehensive job info automatically posted • **No Buttons Required** - Everything happens automatically • **Skills Categorization** - Technical vs soft skills • **Client Verification** - Payment status & history • **Competition Analysis** - Applicant statistics",
        inline=False
    )
    
    embed.set_footer(text="Enhanced with automatic detailed threads for every job!")
    await ctx.send(embed=embed)

async def bhw_monitor_async():
    channel = bot.get_channel(DISCORD_CHANNEL_ID2)
    if channel is None:
        print(f"❌ Could not find channel with ID {DISCORD_CHANNEL_ID2}")
        return
    try:
        # Run post_new_bhw_threads in executor to avoid blocking
        loop = asyncio.get_event_loop()
        approved_threads = await loop.run_in_executor(None, lambda: post_new_bhw_threads(channel))
        if approved_threads:
            import discord
            from db.database import SessionLocal
            from db.models import BHWThread
            session = SessionLocal()
            try:
                for thread in approved_threads:
                    try:
                        embed = discord.Embed(
                            title=thread.title or 'No Title',
                            description=thread.full_description[:1500] if thread.full_description else 'No description',
                            url=thread.link,
                            color=0x00ff00
                        )
                        # Enhanced horizontal layout for BHW threads
                        embed.add_field(name="👤 Author", value=thread.author or 'Unknown', inline=True)
                        embed.add_field(name="💬 Replies", value=str(thread.replies_count or 0), inline=True)
                        embed.add_field(name="👀 Views", value=str(thread.views_count or 0), inline=True)
                        embed.add_field(name="📅 Posted", value=str(thread.posted), inline=True)
                        embed.add_field(name="🏷️ Category", value="BHW Thread", inline=True)
                        embed.add_field(name="⚡ Status", value="New", inline=True)
                        
                        embed.set_footer(text=f"BHW Auto-Monitor • Posted: {thread.posted}")
                        await channel.send(embed=embed)
                        # Mark as posted
                        db_thread = session.query(BHWThread).filter_by(link=thread.link).first()
                        if db_thread:
                            db_thread.posted_to_discord = True
                            session.commit()
                    except Exception as e:
                        print(f"[BHW] Error posting thread to Discord: {e}")
                print(f"✅ Posted {len(approved_threads)} new BHW threads to channel 2.")
            finally:
                session.close()
        else:
            print("ℹ️ No new BHW threads found for channel 2.")
    except Exception as e:
        print(f"❌ Error posting BHW threads: {e}")

async def run_scrapers_concurrently():
    await bot.wait_until_ready()

    # ── One-time startup bootstrap ──────────────────────────────────────────
    # Bootstrap a fresh visitor_gql_token ONCE before launching 25 parallel
    # tasks.  Without this, all tasks start with a stale hardcoded token,
    # immediately get 401, and then all hammer the Upwork homepage
    # simultaneously → 429 rate-limit → nobody gets a fresh token.
    print("[Startup] Bootstrapping fresh Upwork session before first scan...")
    loop = asyncio.get_event_loop()
    bootstrap_ok = await loop.run_in_executor(None, scraper._bootstrap_fresh_session)
    if bootstrap_ok and scraper.current_auth_token:
        print(f"[Startup] ✅ Fresh token acquired: {scraper.current_auth_token[:30]}...")
    else:
        print("[Startup] ⚠️  Bootstrap did not return a fresh OAuth2 token — will retry on first 401.")
    # ── End startup bootstrap ───────────────────────────────────────────────

    while True:
        # Run job searches then wait before next cycle
        await asyncio.gather(
            run_advanced_job_searches()
            # bhw_monitor_async()
        )
        print("[Real-time] Waiting 1 minute before next scan cycle...")
        await asyncio.sleep(60)  # Wait 1 minute between full cycles
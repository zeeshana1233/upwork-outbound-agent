"""
MERIDIAN engine.
- Loads category-partitioned reference corpus from DB (cached 30 min)
- Calls GPT async to score each incoming job
- Returns structured verdict dict
"""
import asyncio
import json
import re
import time
import datetime
from typing import Optional

from openai import AsyncOpenAI

import config
from meridian.prompt import MERIDIAN_PROMPT_TEMPLATE
from meridian import cost_tracker

# ─── Category corpus cache ────────────────────────────────────
# {category: (summary_str, expires_at_epoch)}
_CORPUS_CACHE: dict = {}
CACHE_TTL = 1800  # 30 minutes

# Semaphore: max 3 concurrent GPT calls
_gpt_semaphore = asyncio.Semaphore(3)

# Lazy OpenAI client
_client: Optional[AsyncOpenAI] = None


def _get_client() -> AsyncOpenAI:
    global _client
    if _client is None:
        _client = AsyncOpenAI(api_key=config.OPENAI_API_KEY)
    return _client


# ─── Corpus building ─────────────────────────────────────────

def _build_category_summary(category: str) -> str:
    """Query past_jobs for the given category, return formatted reference text."""
    try:
        from db.database import SessionLocal
        from db.models import PastJob
        with SessionLocal() as session:
            jobs = (
                session.query(PastJob)
                .filter(PastJob.category == category)
                .order_by(PastJob.weight.desc())
                .all()
            )
    except Exception as e:
        print(f"[MERIDIAN] DB error loading corpus for '{category}': {e}")
        return ""

    if not jobs:
        return f"== PAST WORK REFERENCE: {category} ==\n(No reference entries yet for this category.)\n"

    lines = [f"== PAST WORK REFERENCE: {category} ==",
             f"Reference work we have done in this category:\n"]

    for i, job in enumerate(jobs, 1):
        skills_str = ""
        if job.skills:
            try:
                skills_list = json.loads(job.skills)
                skills_str = ", ".join(skills_list)
            except Exception:
                skills_str = job.skills

        budget_str = f"${job.budget:,.0f}" if job.budget else "unknown"
        lines.append(f'{i}. "{job.title}"')
        if job.description:
            lines.append(f"   {job.description[:200]}")
        lines.append(f"   Skills: {skills_str}")
        lines.append(f"   Budget: {budget_str}  |  Outcome: {job.outcome or 'unknown'}\n")

    return "\n".join(lines)


def get_category_summary(category: str) -> str:
    """Return cached or freshly built category summary."""
    cached = _CORPUS_CACHE.get(category)
    if cached and time.time() < cached[1]:
        return cached[0]
    summary = _build_category_summary(category)
    _CORPUS_CACHE[category] = (summary, time.time() + CACHE_TTL)
    return summary


def invalidate_cache(category: str = None):
    """Force cache refresh. Pass None to invalidate all categories."""
    if category:
        _CORPUS_CACHE.pop(category, None)
    else:
        _CORPUS_CACHE.clear()


# ─── Response parsing ─────────────────────────────────────────

def _parse_gpt_response(raw: str) -> dict:
    """
    Parse GPT JSON response. Multiple fallback attempts.
    Defaults to verdict=pass on any parse failure (fail-open).
    """
    # Strip markdown code fences if present
    text = re.sub(r"```(?:json)?", "", raw).strip()

    # Try direct parse
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        # Try to extract the first {...} block
        match = re.search(r"\{.*\}", text, re.DOTALL)
        if match:
            try:
                data = json.loads(match.group())
            except json.JSONDecodeError:
                print(f"[MERIDIAN] JSON parse failed, fail-open. Raw: {raw[:200]}")
                return {"total_score": -1, "verdict": "pass", "reasoning": "parse error (fail-open)"}
        else:
            print(f"[MERIDIAN] No JSON found, fail-open. Raw: {raw[:200]}")
            return {"total_score": -1, "verdict": "pass", "reasoning": "no json (fail-open)"}

    # Ensure verdict follows threshold rule
    total = data.get("total_score", 0)
    threshold = getattr(config, "MERIDIAN_THRESHOLD", 60)
    if total >= 0:  # -1 means parse error — keep verdict as-is
        data["verdict"] = "pass" if total >= threshold else "skip"

    return data


# ─── Main scoring function ────────────────────────────────────

async def run_meridian(job: dict, category: str) -> dict:
    """
    Score one job against its category corpus.
    Returns a dict with keys: domain_fit, scope_clarity, tech_stack_match,
    budget_viability, total_score, verdict, reasoning.
    Never raises — returns fail-open dict on any error.
    """
    FAIL_OPEN = {"total_score": -1, "verdict": "pass", "reasoning": "meridian error (fail-open)"}

    if not config.OPENAI_API_KEY:
        print("[MERIDIAN] OPENAI_API_KEY not set, skipping scoring")
        return FAIL_OPEN

    category_summary = get_category_summary(category)
    threshold        = getattr(config, "MERIDIAN_THRESHOLD", 60)
    model            = getattr(config, "OPENAI_MODEL", "gpt-4o-mini")

    # Build skills string
    raw_skills = job.get("skills") or []
    if isinstance(raw_skills, list):
        skills_str = ", ".join(raw_skills)
    elif isinstance(raw_skills, str):
        skills_str = raw_skills
    else:
        skills_str = str(raw_skills)

    # Build budget string
    budget_raw = job.get("budget")
    if budget_raw:
        budget_str = f"${budget_raw}"
    else:
        budget_str = "unknown"

    prompt = MERIDIAN_PROMPT_TEMPLATE.format(
        category_reference_summary = category_summary,
        title       = (job.get("title") or "")[:300],
        description = (job.get("description") or "")[:1500],
        skills      = skills_str[:300],
        budget      = budget_str,
        threshold   = threshold,
    )

    try:
        async with _gpt_semaphore:
            client   = _get_client()
            response = await client.chat.completions.create(
                model    = model,
                messages = [{"role": "user", "content": prompt}],
                temperature     = 0.0,
                max_tokens      = 200,
                response_format = {"type": "json_object"},
            )

        usage      = response.usage
        call_pkr   = cost_tracker.record_call(usage.prompt_tokens, usage.completion_tokens)
        raw_reply  = response.choices[0].message.content or ""
        result     = _parse_gpt_response(raw_reply)
        result["_cost_pkr"] = call_pkr
        return result

    except Exception as e:
        print(f"[MERIDIAN] GPT call error for '{job.get('title','?')[:40]}': {e}")
        return FAIL_OPEN


# Alias used in discord_bot.py
get_meridian_verdict = run_meridian

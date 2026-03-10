"""
Module 3 — Proposal draft generator.

Triggered by: WhatsApp message "agree <job_number>"
Uses: MERIDIAN reasoning already stored in DB + category corpus from past_jobs
Returns: plain-text proposal draft ready to paste into Upwork
"""
import json
import os
import datetime
from typing import Optional

from openai import AsyncOpenAI

import config
from meridian.engine import get_category_summary

# Lazy OpenAI client (shared module-level singleton)
_client: Optional[AsyncOpenAI] = None


def _get_client() -> AsyncOpenAI:
    global _client
    if _client is None:
        _client = AsyncOpenAI(api_key=config.OPENAI_API_KEY)
    return _client


# ─── Prompt template ─────────────────────────────────────────────────────────

PROPOSAL_PROMPT_TEMPLATE = """\
You are a senior freelancer writing a winning Upwork proposal.
Your writing style: concise, confident, no filler phrases, no "I hope this finds you well".
Open directly with the client's core problem. Mirror their language. Show relevant proof.
End with ONE clear CTA question that moves the conversation forward.

Target word count: 120–180 words. Never exceed 220 words.

== CLIENT JOB ==
Title: {title}
Budget: {budget}
Description:
{description}

== RELEVANT SKILLS ==
{skills}

== WHY THIS JOB MATCHED (MERIDIAN AI analysis) ==
{meridian_reasoning}

== OUR PAST WORK IN THIS CATEGORY ==
{category_reference}

== INSTRUCTIONS ==
Write the proposal now. Plain text only — no markdown, no bullet points, no headers.
Do not include a subject line or greeting ("Dear client" etc).
Start directly with the hook sentence addressing their problem.
"""


# ─── Job lookup ──────────────────────────────────────────────────────────────

def get_job_by_number(job_number: int) -> Optional[dict]:
    """
    Look up a Job row by its human-readable job_number.
    Returns a plain dict or None if not found.
    """
    try:
        from db.database import SessionLocal
        from db.models import Job
        with SessionLocal() as session:
            row = session.query(Job).filter(Job.job_number == job_number).first()
            if not row:
                return None
            return {
                "job_id":            row.job_id,
                "job_number":        row.job_number,
                "title":             row.title or "",
                "description":       row.description or "",
                "budget":            row.budget,
                "skills":            row.skills or "",
                "meridian_reasoning": row.meridian_reasoning or "",
                "meridian_verdict":  row.meridian_verdict or "",
                "discord_message_id": row.discord_message_id,
            }
    except Exception as e:
        print(f"[PROPOSALS] DB lookup error for job #{job_number}: {e}")
        return None


# ─── Draft saver ─────────────────────────────────────────────────────────────

def save_proposal_draft(job_id: str, job_number: int, draft_text: str) -> int:
    """
    Persist the generated draft to the proposals table.
    Returns the new proposal row id, or -1 on failure.
    """
    try:
        from db.database import SessionLocal
        from db.models import Proposal
        with SessionLocal() as session:
            row = Proposal(
                job_id=job_id,
                job_number=job_number,
                draft_text=draft_text,
                status="draft",
                generated_at=datetime.datetime.utcnow(),
            )
            session.add(row)
            session.commit()
            session.refresh(row)
            return row.id
    except Exception as e:
        print(f"[PROPOSALS] DB save error for job #{job_number}: {e}")
        return -1


# ─── Prompt logger ───────────────────────────────────────────────────────────

def _save_prompt_to_file(job_number: int, title: str, job_id: str, category: str, prompt: str, model: str):
    """
    Save the exact prompt string that is about to be sent to OpenAI.
    File: proposals/prompts/job_NNN_YYYY-MM-DD_HH-MM-SS.md
    The content between the dividers is byte-for-byte what GPT receives.
    """
    try:
        prompts_dir = os.path.join(os.path.dirname(__file__), "prompts")
        os.makedirs(prompts_dir, exist_ok=True)

        now = datetime.datetime.utcnow()
        timestamp = now.strftime("%Y-%m-%d_%H-%M-%S")
        filename = f"job_{job_number:03d}_{timestamp}.md"
        filepath = os.path.join(prompts_dir, filename)

        header = (
            f"# Proposal Prompt — Job #{job_number}\n"
            f"Generated: {now.strftime('%Y-%m-%d %H:%M:%S')} UTC\n"
            f"Job: {title}\n"
            f"Job ID: {job_id}\n"
            f"Category: {category}\n"
            f"Model: {model} | Temp: 0.7 | Max tokens: 400\n\n"
            f"{'─' * 65}\n"
        )
        footer = f"\n{'─' * 65}\n"

        with open(filepath, "w", encoding="utf-8") as f:
            f.write(header)
            f.write(prompt)
            f.write(footer)

        print(f"[PROPOSALS] Prompt saved → proposals/prompts/{filename}")
    except Exception as e:
        print(f"[PROPOSALS] Failed to save prompt file (non-fatal): {e}")


# ─── Main generation function ─────────────────────────────────────────────────

async def generate_proposal(job_number: int) -> dict:
    """
    Generate a proposal draft for the given human job_number.

    Returns:
        {
            "ok": True,
            "job_number": int,
            "title": str,
            "draft": str,
            "proposal_id": int,
        }
    or on failure:
        {
            "ok": False,
            "error": str,
        }
    """
    if not config.OPENAI_API_KEY:
        return {"ok": False, "error": "OPENAI_API_KEY not set"}

    # 1. Load the job from DB
    job = get_job_by_number(job_number)
    if not job:
        return {"ok": False, "error": f"No job found with number #{job_number}"}

    # 2. Detect category from the job skills / title to pull correct corpus.
    #    We infer it by checking which category in past_jobs has the closest match.
    #    For now we use a simple keyword heuristic — good enough given our category set.
    category = _infer_category(job)

    # 3. Load reference corpus for this category
    category_reference = get_category_summary(category)

    # 4. Build budget string
    budget_raw = job.get("budget")
    budget_str = f"${budget_raw}" if budget_raw else "Not specified"

    # 5. Build skills string
    skills_raw = job.get("skills") or ""
    if skills_raw.startswith("["):
        try:
            skills_str = ", ".join(json.loads(skills_raw))
        except Exception:
            skills_str = skills_raw
    else:
        skills_str = skills_raw

    # 6. Build the prompt
    prompt = PROPOSAL_PROMPT_TEMPLATE.format(
        title              = job["title"][:300],
        budget             = budget_str,
        description        = (job["description"] or "")[:2000],
        skills             = skills_str[:400],
        meridian_reasoning = (job["meridian_reasoning"] or "No MERIDIAN analysis available.")[:600],
        category_reference = category_reference[:1500],
    )

    # 6b. Save exact prompt to file for inspection
    _save_prompt_to_file(job_number, job["title"], job["job_id"], category, prompt, getattr(config, "OPENAI_MODEL", "gpt-4o-mini"))

    # 7. Call GPT
    try:
        client = _get_client()
        response = await client.chat.completions.create(
            model       = getattr(config, "OPENAI_MODEL", "gpt-4o-mini"),
            messages    = [{"role": "user", "content": prompt}],
            temperature = 0.7,
            max_tokens  = 400,
        )
        draft = (response.choices[0].message.content or "").strip()
    except Exception as e:
        print(f"[PROPOSALS] GPT error for job #{job_number}: {e}")
        return {"ok": False, "error": f"GPT call failed: {e}"}

    if not draft:
        return {"ok": False, "error": "GPT returned empty draft"}

    # 8. Save to DB
    proposal_id = save_proposal_draft(job["job_id"], job_number, draft)

    return {
        "ok":          True,
        "job_number":  job_number,
        "title":       job["title"],
        "draft":       draft,
        "proposal_id": proposal_id,
        "job_id":      job["job_id"],
    }


# ─── Category inference ───────────────────────────────────────────────────────

# Maps known category strings (from job_search_keywords.py) to corpus keys
_CATEGORY_KEYWORD_MAP = {
    "Android Automation":  ["android", "adb", "appium", "emulator", "phone farm", "mobile farm"],
    "Stealth Automation":  ["multilogin", "gologin", "antidetect", "fingerprint", "residential proxy",
                            "incognition", "adspower", "dolphin"],
    "Social Media & SMM":  ["smm", "twitter", "instagram", "telegram", "follower", "engagement", "tiktok comment"],
    "TikTok Shop":         ["tiktok shop", "tiktok affiliate", "tiktok outreach"],
    "AI Automation":       ["openai", "langchain", "rag", "chatgpt", "llm", "chatbot", "huggingface",
                            "vector database", "gpt developer", "ai agent", "n8n", "zapier", "make.com"],
    "Web Development":     ["react", "next.js", "nextjs", "django", "flask", "node.js", "nodejs",
                            "fastapi", "mern", "full stack"],
    "Automation":          ["selenium", "puppeteer", "playwright", "bot", "browser automation",
                            "python script", "workflow automation"],
}


def _infer_category(job: dict) -> str:
    """
    Heuristic: scan the job title + skills for keywords to pick the best corpus category.
    Falls back to 'Automation' if nothing matches.
    """
    haystack = " ".join([
        job.get("title", ""),
        job.get("skills", ""),
        job.get("description", "")[:500],
    ]).lower()

    best_category = "Automation"
    best_score    = 0

    for category, keywords in _CATEGORY_KEYWORD_MAP.items():
        score = sum(1 for kw in keywords if kw in haystack)
        if score > best_score:
            best_score    = score
            best_category = category

    return best_category

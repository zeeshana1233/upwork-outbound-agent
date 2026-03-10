"""
Discord notification layer for MERIDIAN and proposals.

Sends MERIDIAN match/skip verdicts, cycle cost reports, and proposal drafts
to the #meridian-alerts channel on the same Discord server as the job channels.

Channel is configured via MERIDIAN_DISCORD_CHANNEL_ID in .env.
Set to 0 (or omit) to disable Discord notifications silently.

Usage:
    from bot.discord_notifier import send_meridian_discord, send_proposal_discord

All functions are fire-and-forget safe (never raise).
"""
from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING

import config

if TYPE_CHECKING:
    import discord as _discord

# Module-level bot reference — injected once on_ready fires in discord_bot.py
_bot_ref = None


def set_bot(bot) -> None:
    """Called once from discord_bot.py after the bot is ready."""
    global _bot_ref
    _bot_ref = bot


def _get_channel():
    """Return the #meridian-alerts channel object, or None if unavailable."""
    channel_id = getattr(config, "MERIDIAN_DISCORD_CHANNEL_ID", 0)
    if not channel_id:
        return None
    if _bot_ref is None:
        return None
    return _bot_ref.get_channel(channel_id)


# ─── Discord message builders ────────────────────────────────────────────────
# These produce the same information as the WA builders but without the
# 1000-char limit — Discord allows up to 2000 chars per plain message.

def build_discord_match_message(job: dict, result: dict, category: str,
                                cost_pkr: float = 0.0,
                                job_number: int = 0) -> str:
    title       = job.get("title") or "Untitled"
    budget_raw  = job.get("budget")
    job_id      = job.get("id") or job.get("ciphertext") or ""
    clean_id    = str(job_id).lstrip("~") if job_id else ""
    job_url     = f"https://www.upwork.com/freelance-jobs/apply/~{clean_id}" if clean_id else "N/A"
    budget_str  = f"${budget_raw}" if budget_raw else "Unknown"

    raw_skills  = job.get("skills") or []
    if isinstance(raw_skills, list):
        skills_str = " • ".join(raw_skills[:10]) + (" • ..." if len(raw_skills) > 10 else "")
    else:
        skills_str = str(raw_skills)[:200]

    total     = result.get("total_score", "?")
    domain    = result.get("domain_fit", "?")
    clarity   = result.get("scope_clarity", "?")
    tech      = result.get("tech_stack_match", "?")
    budget_v  = result.get("budget_viability", "?")
    reasoning = result.get("reasoning", "")
    cat_label = category.replace("_", " ").title()

    job_num_line = f"**Job #:** {job_number}  ·  Reply **agree {job_number}** to draft a proposal\n" if job_number and job_number > 0 else ""

    return (
        f"## 🎯 MERIDIAN MATCH — Score: {total}/100\n\n"
        f"**Title:** {title}\n"
        f"**Budget:** {budget_str}  |  **Category:** {cat_label}\n"
        f"**Skills:** `{skills_str}`\n\n"
        f"**Why it matched:**\n{reasoning}\n\n"
        f"{job_url}\n\n"
        f"{job_num_line}"
        f"```\n"
        f"Domain: {domain}/40  |  Clarity: {clarity}/25  |  Tech: {tech}/20  |  Budget: {budget_v}/15\n"
        f"Cost: ₨ {cost_pkr:.4f} PKR\n"
        f"```"
    )


def build_discord_skip_message(job: dict, result: dict, category: str,
                               cost_pkr: float = 0.0) -> str:
    title      = job.get("title") or "Untitled"
    budget_raw = job.get("budget")
    job_id     = job.get("id") or job.get("ciphertext") or ""
    clean_id   = str(job_id).lstrip("~") if job_id else ""
    job_url    = f"https://www.upwork.com/freelance-jobs/apply/~{clean_id}" if clean_id else "N/A"
    budget_str = f"${budget_raw}" if budget_raw else "Unknown"
    cat_label  = category.replace("_", " ").title()

    total     = result.get("total_score", "?")
    domain    = result.get("domain_fit", "?")
    clarity   = result.get("scope_clarity", "?")
    tech      = result.get("tech_stack_match", "?")
    budget_v  = result.get("budget_viability", "?")
    reasoning = result.get("reasoning", "")
    threshold = getattr(config, "MERIDIAN_THRESHOLD", 60)

    return (
        f"## ❌ MERIDIAN SKIP — Score: {total}/100 (threshold: {threshold})\n\n"
        f"**Title:** {title}\n"
        f"**Budget:** {budget_str}  |  **Category:** {cat_label}\n\n"
        f"**Why it was skipped:**\n{reasoning}\n\n"
        f"{job_url}\n\n"
        f"```\n"
        f"Domain: {domain}/40  |  Clarity: {clarity}/25  |  Tech: {tech}/20  |  Budget: {budget_v}/15\n"
        f"Cost: ₨ {cost_pkr:.4f} PKR\n"
        f"```"
    )


def build_discord_proposal_message(result: dict) -> str:
    job_number  = result.get("job_number", "?")
    title       = result.get("title", "Untitled")
    draft       = result.get("draft", "")
    proposal_id = result.get("proposal_id", "?")
    job_id      = result.get("job_id", "")
    clean_id    = str(job_id).lstrip("~") if job_id else ""
    job_url     = f"https://www.upwork.com/freelance-jobs/apply/~{clean_id}" if clean_id else "N/A"

    return (
        f"## ✍️ PROPOSAL DRAFT — Job #{job_number}\n\n"
        f"**Title:** {title}\n"
        f"{job_url}\n\n"
        f"```\n{draft}\n```\n\n"
        f"*Proposal ID: {proposal_id}  ·  Reply `agree {job_number}` to regenerate*"
    )


def build_discord_proposal_error_message(job_number: int, error: str) -> str:
    return (
        f"## ⚠️ PROPOSAL FAILED — Job #{job_number}\n\n"
        f"Could not generate draft:\n> {error}\n\n"
        f"Check that job #{job_number} exists and has been scored by MERIDIAN."
    )


# ─── Async send helpers ───────────────────────────────────────────────────────

async def send_to_meridian_channel(message: str) -> bool:
    """
    Send a plain-text message to #meridian-alerts.
    Returns True on success, False on any failure (never raises).
    Discord has a 2000-char limit; long messages are split automatically.
    """
    channel = _get_channel()
    if channel is None:
        ch_id = getattr(config, "MERIDIAN_DISCORD_CHANNEL_ID", 0)
        if ch_id:
            print(f"[DISCORD-NOTIFIER] Channel {ch_id} not found (bot not ready or wrong ID)")
        return False

    try:
        # Discord limit: 2000 chars per message — split if needed
        max_len = 1990
        if len(message) <= max_len:
            await channel.send(message)
        else:
            # Split on newlines where possible
            chunks = []
            current = ""
            for line in message.splitlines(keepends=True):
                if len(current) + len(line) > max_len:
                    chunks.append(current)
                    current = line
                else:
                    current += line
            if current:
                chunks.append(current)
            for chunk in chunks:
                await channel.send(chunk)
                await asyncio.sleep(0.3)
        return True
    except Exception as e:
        print(f"[DISCORD-NOTIFIER] Send error: {e}")
        return False


async def send_meridian_discord(job: dict, result: dict, category: str,
                                cost_pkr: float = 0.0,
                                job_number: int = 0,
                                verdict: str = "pass") -> bool:
    """
    Send MERIDIAN verdict (match or skip) to #meridian-alerts.
    verdict='pass' → match message, verdict='skip' → skip message.
    """
    if verdict == "pass":
        msg = build_discord_match_message(job, result, category, cost_pkr, job_number)
    else:
        msg = build_discord_skip_message(job, result, category, cost_pkr)
    return await send_to_meridian_channel(msg)


async def send_proposal_discord(result: dict) -> bool:
    """
    Send a proposal draft (or error) to #meridian-alerts.
    result is the dict returned by generate_proposal().
    """
    if result.get("ok"):
        msg = build_discord_proposal_message(result)
    else:
        job_number = result.get("job_number", "?")
        error      = result.get("error", "unknown error")
        msg        = build_discord_proposal_error_message(job_number, error)
    return await send_to_meridian_channel(msg)


async def send_cost_report_discord(report: str) -> bool:
    """Send the MERIDIAN cycle cost report to #meridian-alerts."""
    return await send_to_meridian_channel(report)

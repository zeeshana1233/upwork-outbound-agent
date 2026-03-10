"""
MERIDIAN WhatsApp delivery layer.
Calls the Baileys Node.js bridge via HTTP POST.
"""
import httpx
import config


async def send_whatsapp(group_jid: str, message: str) -> bool:
    """
    Send a message to a WhatsApp group via the Baileys bridge.
    Returns True on success, False on any failure (never raises).
    """
    if not group_jid:
        print("[MERIDIAN] WA_GROUP_JID is empty — skipping WhatsApp send")
        return False

    bridge_url = getattr(config, "WA_BRIDGE_URL", "http://localhost:3001/send")
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.post(
                bridge_url,
                json={"group_jid": group_jid, "message": message},
            )
            if resp.status_code == 200:
                return True
            else:
                print(f"[MERIDIAN] WhatsApp bridge returned {resp.status_code}: {resp.text[:100]}")
                return False
    except httpx.ConnectError:
        print("[MERIDIAN] WhatsApp bridge not reachable (is node server.js running?)")
        return False
    except Exception as e:
        print(f"[MERIDIAN] WhatsApp send error: {e}")
        return False


def build_wa_job_message(job: dict, result: dict, category: str, cost_pkr: float = 0.0) -> str:
    """
    Build the WhatsApp job notification message.
    """
    title       = job.get("title") or "Untitled"
    budget_raw  = job.get("budget")
    job_id      = job.get("id") or job.get("ciphertext") or ""

    # Build URL
    clean_id = str(job_id).lstrip("~") if job_id else ""
    job_url  = f"https://www.upwork.com/freelance-jobs/apply/~{clean_id}" if clean_id else "N/A"

    # Budget display
    if budget_raw:
        budget_str = f"${budget_raw}"
    else:
        budget_str = "Unknown"

    # Skills
    raw_skills = job.get("skills") or []
    if isinstance(raw_skills, list):
        skills_str = " • ".join(raw_skills[:8]) + (" • ..." if len(raw_skills) > 8 else "")
    else:
        skills_str = str(raw_skills)[:150]

    # Scores
    total    = result.get("total_score", "?")
    domain   = result.get("domain_fit", "?")
    clarity  = result.get("scope_clarity", "?")
    tech     = result.get("tech_stack_match", "?")
    budget_v = result.get("budget_viability", "?")
    reasoning = result.get("reasoning", "")

    # Category label — title case
    cat_label = category.replace("_", " ").title()

    msg = (
        f"🎯 *MERIDIAN MATCH* — Score: {total}/100\n\n"
        f"*Title:* {title}\n"
        f"*Budget:* {budget_str}\n"
        f"*Category:* {cat_label}\n"
        f"*Skills:* {skills_str}\n\n"
        f"*Why it matched:*\n{reasoning}\n\n"
        f"🔗 {job_url}\n\n"
        f"{'─' * 29}\n"
        f"Domain: {domain}/40 | Clarity: {clarity}/25 | Tech: {tech}/20 | Budget: {budget_v}/15\n"
        f"💰 This job: ₨ {cost_pkr:.4f} PKR"
    )
    return msg


def build_wa_skip_message(job: dict, result: dict, category: str, cost_pkr: float = 0.0) -> str:
    """
    Build a compact WhatsApp notification for a MERIDIAN-rejected job.
    """
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
        f"❌ *MERIDIAN SKIP* — Score: {total}/100 (threshold: {threshold})\n\n"
        f"*Title:* {title}\n"
        f"*Budget:* {budget_str}\n"
        f"*Category:* {cat_label}\n\n"
        f"*Why it was skipped:*\n{reasoning}\n\n"
        f"🔗 {job_url}\n\n"
        f"{'─' * 29}\n"
        f"Domain: {domain}/40 | Clarity: {clarity}/25 | Tech: {tech}/20 | Budget: {budget_v}/15\n"
        f"💰 This job: ₨ {cost_pkr:.4f} PKR"
    )

"""
Module 3 — WhatsApp proposal delivery.
Builds and sends the draft message via the same Baileys bridge used by MERIDIAN.
"""
import httpx
import config


def build_wa_proposal_message(result: dict) -> str:
    """
    Build the WhatsApp message that delivers a proposal draft.
    result is the dict returned by generate_proposal().
    """
    job_number  = result.get("job_number", "?")
    title       = result.get("title", "Untitled")
    draft       = result.get("draft", "")
    proposal_id = result.get("proposal_id", "?")

    job_id    = result.get("job_id", "")
    clean_id  = str(job_id).lstrip("~") if job_id else ""
    job_url   = f"https://www.upwork.com/freelance-jobs/apply/~{clean_id}" if clean_id else "N/A"

    return (
        f"✍️ *PROPOSAL DRAFT — Job #{job_number}*\n\n"
        f"*Title:* {title}\n"
        f"🔗 {job_url}\n\n"
        f"{'─' * 29}\n\n"
        f"{draft}\n\n"
        f"{'─' * 29}\n"
        f"_Proposal ID: {proposal_id} | Reply 'agree {job_number}' to regenerate_"
    )


def build_wa_error_message(job_number: int, error: str) -> str:
    """Build a short error message for WA when draft generation fails."""
    return (
        f"⚠️ *PROPOSAL FAILED — Job #{job_number}*\n\n"
        f"Could not generate draft:\n_{error}_\n\n"
        f"Check that job #{job_number} exists and has been scored by MERIDIAN."
    )


async def send_proposal_via_whatsapp(result: dict) -> bool:
    """
    Send the proposal draft (or error) to WhatsApp.
    result is from generate_proposal().
    Returns True on successful WA delivery.
    """
    group_jid = getattr(config, "WA_GROUP_JID", "")
    if not group_jid:
        print("[PROPOSALS] WA_GROUP_JID is empty — skipping WhatsApp send")
        return False

    if result.get("ok"):
        message = build_wa_proposal_message(result)
    else:
        job_number = result.get("job_number", "?")
        error      = result.get("error", "unknown error")
        message    = build_wa_error_message(job_number, error)

    bridge_url = getattr(config, "WA_BRIDGE_URL", "http://localhost:3001/send")
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.post(
                bridge_url,
                json={"group_jid": group_jid, "message": message},
            )
            if resp.status_code == 200:
                print(f"[PROPOSALS] Draft delivered to WhatsApp (job #{result.get('job_number', '?')})")
                return True
            else:
                print(f"[PROPOSALS] WA bridge returned {resp.status_code}: {resp.text[:100]}")
                return False
    except httpx.ConnectError:
        print("[PROPOSALS] WA bridge not reachable (is node server.js running?)")
        return False
    except Exception as e:
        print(f"[PROPOSALS] WA send error: {e}")
        return False

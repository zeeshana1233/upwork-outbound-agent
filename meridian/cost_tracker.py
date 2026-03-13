"""
MERIDIAN cost tracker.
Tracks GPT token usage per scan cycle, calculates PKR cost, persists to DB.

Pricing (gpt-4o-mini):
  Input:  $0.150 / 1M tokens
  Output: $0.600 / 1M tokens
"""
import datetime
from threading import Lock

import config

# Per-model pricing table (USD per 1M tokens)
MODEL_PRICING = {
    "gpt-4o-mini": {"input": 0.150, "output": 0.600},
}
DEFAULT_PRICING = {"input": 0.150, "output": 0.600}

_lock = Lock()

# Cycle accumulators (reset after each flush)
_cycle_input_tokens: int = 0
_cycle_output_tokens: int = 0
_cycle_jobs_scored: int = 0

# Running session total (in-memory, persisted to DB on flush)
_session_total_pkr: float = 0.0

# Cost of the most recent single GPT call (for per-job WA message)
_last_call_cost_pkr: float = 0.0


def _pricing():
    model = getattr(config, "OPENAI_MODEL", "gpt-4o-mini")
    return MODEL_PRICING.get(model, DEFAULT_PRICING)


def _usd_to_pkr(usd: float) -> float:
    rate = getattr(config, "PKR_PER_USD", 280.0)
    return usd * rate


def record_call(input_tokens: int, output_tokens: int) -> float:
    """
    Record token usage for one GPT call.
    Returns the PKR cost of this single call.
    """
    global _cycle_input_tokens, _cycle_output_tokens, _cycle_jobs_scored
    global _last_call_cost_pkr, _session_total_pkr

    pricing = _pricing()
    call_usd = (input_tokens * pricing["input"] + output_tokens * pricing["output"]) / 1_000_000
    call_pkr = _usd_to_pkr(call_usd)

    with _lock:
        _cycle_input_tokens  += input_tokens
        _cycle_output_tokens += output_tokens
        _cycle_jobs_scored   += 1
        _last_call_cost_pkr   = call_pkr
        _session_total_pkr   += call_pkr

    return call_pkr


def get_last_call_cost_pkr() -> float:
    """Return PKR cost of the most recent GPT call."""
    return _last_call_cost_pkr


def get_session_total_pkr() -> float:
    """Return running PKR total since bot start (in-memory)."""
    return _session_total_pkr


def flush_cycle_report() -> str:
    """
    Build the per-cycle WhatsApp finance message, persist to DB, reset counters.
    Returns the formatted message string, or empty string if no GPT calls were made.
    """
    global _cycle_input_tokens, _cycle_output_tokens, _cycle_jobs_scored
    global _session_total_pkr

    with _lock:
        inp    = _cycle_input_tokens
        out    = _cycle_output_tokens
        scored = _cycle_jobs_scored

        # No real GPT calls this cycle — send nothing
        if inp == 0 and out == 0:
            _cycle_input_tokens  = 0
            _cycle_output_tokens = 0
            _cycle_jobs_scored   = 0
            return ""

        pricing  = _pricing()
        cost_usd = (inp * pricing["input"] + out * pricing["output"]) / 1_000_000
        cost_pkr = _usd_to_pkr(cost_usd)
        session  = _session_total_pkr

        # Reset cycle counters
        _cycle_input_tokens  = 0
        _cycle_output_tokens = 0
        _cycle_jobs_scored   = 0

    # Persist and get all-time DB total
    _persist_to_db(scored, inp, out, cost_usd, cost_pkr, session)
    alltime_pkr = _get_alltime_total_pkr()
    remaining_pkr, remaining_usd = _get_estimated_remaining(alltime_pkr)

    now_utc = datetime.datetime.utcnow().strftime("%H:%M UTC")
    model   = getattr(config, "OPENAI_MODEL", "gpt-4o-mini")

    return (
        f"💰 *MERIDIAN Finance Report*\n"
        f"🕐 Cycle: {now_utc} | Jobs scored: {scored}\n\n"
        f"Model: {model}\n"
        f"GPT calls: {scored}\n"
        f"Input tokens: {inp:,} | Output tokens: {out:,}\n"
        f"Cost: ${cost_usd:.4f} → ₨ {cost_pkr:.2f} PKR\n\n"
        f"📊 This session: ₨ {session:.2f} PKR\n"
        f"📈 All-time total: ₨ {alltime_pkr:.2f} PKR\n"
        f"💳 Est. remaining: ₨ {remaining_pkr:.2f} PKR (~${remaining_usd:.2f})\n"
        f"🔗 platform.openai.com/billing"
    )


def _get_alltime_total_pkr() -> float:
    """Sum all cost_pkr rows from meridian_cost_log table."""
    try:
        from db.database import SessionLocal
        from db.models import MeridianCostLog
        from sqlalchemy import func
        with SessionLocal() as session:
            total = session.query(func.sum(MeridianCostLog.cost_pkr)).scalar()
            return float(total or 0.0)
    except Exception:
        return _session_total_pkr


def _get_estimated_remaining(alltime_pkr: float) -> tuple:
    """
    Return (remaining_pkr, remaining_usd) based on hardcoded credit minus all-time spend.
    Uses OPENAI_CREDIT_USD from config and PKR_PER_USD exchange rate.
    """
    credit_usd  = getattr(config, "OPENAI_CREDIT_USD", 5.00)
    rate        = getattr(config, "PKR_PER_USD", 280.0)
    alltime_usd = alltime_pkr / rate
    remaining_usd = max(0.0, credit_usd - alltime_usd)
    remaining_pkr = remaining_usd * rate
    return remaining_pkr, remaining_usd


def _persist_to_db(jobs_scored, inp, out, cost_usd, cost_pkr, session_total):
    try:
        from db.database import SessionLocal
        from db.models import MeridianCostLog
        with SessionLocal() as session:
            row = MeridianCostLog(
                cycle_at         = datetime.datetime.utcnow(),
                jobs_scored      = jobs_scored,
                input_tokens     = inp,
                output_tokens    = out,
                cost_usd         = cost_usd,
                cost_pkr         = cost_pkr,
                session_total_pkr= session_total,
            )
            session.add(row)
            session.commit()
    except Exception as e:
        print(f"[MERIDIAN] cost_tracker DB persist failed: {e}")

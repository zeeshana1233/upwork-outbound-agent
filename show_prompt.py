from db.database import SessionLocal
from db.models import Job, PastJob
from sqlalchemy import desc, func
from meridian.engine import get_category_summary
from meridian.prompt import MERIDIAN_PROMPT_TEMPLATE
import config

# Get available categories from past_jobs
with SessionLocal() as s:
    jobs = (
        s.query(Job)
        .filter(Job.meridian_score != None)
        .order_by(desc(Job.meridian_run_at))
        .limit(3)
        .all()
    )
    # Pick the most populated category as the corpus example
    top_category = (
        s.query(PastJob.category, func.count(PastJob.id).label("cnt"))
        .group_by(PastJob.category)
        .order_by(desc("cnt"))
        .first()
    )
    category = top_category[0] if top_category else "Android Automation"

for idx, job in enumerate(jobs, 1):
    title    = job.title or ""
    desc_    = (job.description or "")[:600]
    skills   = job.skills or "Not listed"
    budget   = str(job.budget) if job.budget else "Not specified"

    summary = get_category_summary(category)

    prompt = MERIDIAN_PROMPT_TEMPLATE.format(
        category_reference_summary=summary,
        title=title,
        description=desc_,
        skills=skills,
        budget=budget,
        threshold=config.MERIDIAN_THRESHOLD,
    )

    print(f"\n{'#'*70}")
    print(f"EXAMPLE {idx} — Score: {job.meridian_score}/100 | Verdict: {job.meridian_verdict.upper()}")
    print(f"{'#'*70}\n")
    print(prompt)
    print()

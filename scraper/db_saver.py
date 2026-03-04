# scraper/db_saver.py
"""
Handles saving jobs to the database for UpworkScraper.
"""

def save_jobs_to_db(jobs_data):
    """Save jobs to database with corrected field mapping and proper data types.

    Fields saved:
      - job_id, title, budget_numeric  (always)
      - description  (FULL text — no truncation; Discord truncates for display)
      - skills       (JSON-encoded list, e.g. '["Python","Web Scraping"]')
    """
    import json as _json
    from db.database import SessionLocal
    from db.models import Job
    try:
        session = SessionLocal()
        saved_count = 0
        skipped_count = 0

        # Detect which columns the Job table actually has (safe for schema drift)
        try:
            from sqlalchemy import inspect as _inspect
            _column_names = {c.name for c in _inspect(Job).columns}
        except Exception:
            _column_names = {"id", "job_id", "title", "description", "budget", "skills", "posted_at"}

        for job in jobs_data:
            try:
                job_id = job["id"]

                # Skip jobs already stored — avoids UniqueViolation on the job_id index
                if session.query(Job.id).filter_by(job_id=job_id).first():
                    skipped_count += 1
                    continue

                job_fields = {
                    "job_id":  job_id,
                    "title":   job["title"],
                    "budget":  job["budget_numeric"],
                }

                # Full description — NOT truncated; Discord message layer handles display length
                if "description" in _column_names:
                    job_fields["description"] = job.get("description") or ""

                # Skills — stored as JSON array string for easy querying and display
                if "skills" in _column_names:
                    raw_skills = job.get("skills") or []
                    job_fields["skills"] = _json.dumps(raw_skills) if raw_skills else None

                session.add(Job(**job_fields))
                saved_count += 1
            except Exception as e:
                print(f"Error saving job to DB: {e} | {job.get('id', '?')} - {job.get('title', 'No title')}")
                session.rollback()
                continue

        session.commit()
        session.close()
        if saved_count:
            print(f"Saved {saved_count} new jobs to database ({skipped_count} already existed)")
    except Exception as e:
        print(f"Database error: {e}")
        if 'session' in locals():
            session.rollback()
            session.close()

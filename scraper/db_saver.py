# scraper/db_saver.py
"""
Handles saving jobs to the database for UpworkScraper.
"""

def save_jobs_to_db(jobs_data):
    """Save jobs to database with corrected field mapping and proper data types"""
    from db.database import SessionLocal
    from db.models import Job
    try:
        session = SessionLocal()
        saved_count = 0
        skipped_count = 0
        for job in jobs_data:
            try:
                job_id = job["id"]

                # Skip jobs already stored — avoids UniqueViolation on the job_id index
                if session.query(Job.id).filter_by(job_id=job_id).first():
                    skipped_count += 1
                    continue

                job_fields = {
                    "job_id": job_id,
                    "title": job["title"],
                    "budget": job["budget_numeric"],
                    "client": job["client"]
                }
                try:
                    from sqlalchemy import inspect
                    mapper = inspect(Job)
                    column_names = [column.name for column in mapper.columns]
                    if 'description' in column_names:
                        job_fields["description"] = job["description"]
                except Exception:
                    pass
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

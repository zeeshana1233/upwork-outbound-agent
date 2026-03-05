#!/usr/bin/env python3
"""
MERIDIAN seeder.
Loads meridian/data/past_jobs.yaml into the past_jobs DB table.

Usage:
    python -m meridian.seeder            # load YAML (skip existing by title)
    python -m meridian.seeder --reset    # drop all past_jobs rows first, then re-seed
    python -m meridian.seeder --count    # just print row counts per category
"""
import argparse
import json
import os
import sys

# Ensure project root is on the path when run as a script
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import yaml
from dotenv import load_dotenv
load_dotenv()

from db.database import SessionLocal, engine
from db.models import Base, PastJob


YAML_PATH = os.path.join(os.path.dirname(__file__), "data", "past_jobs.yaml")


def ensure_tables():
    """Create tables if they don't exist yet."""
    Base.metadata.create_all(bind=engine)


def load_yaml() -> list:
    with open(YAML_PATH, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)
    return data or []


def seed(reset: bool = False):
    ensure_tables()
    entries = load_yaml()

    with SessionLocal() as session:
        if reset:
            deleted = session.query(PastJob).delete()
            session.commit()
            print(f"[seeder] Deleted {deleted} existing past_jobs rows.")

        inserted = 0
        skipped  = 0
        for entry in entries:
            title = entry.get("title", "").strip()
            if not title:
                continue

            existing = session.query(PastJob).filter(PastJob.title == title).first()
            if existing:
                skipped += 1
                continue

            skills = entry.get("skills")
            if isinstance(skills, list):
                skills_str = json.dumps(skills)
            elif isinstance(skills, str):
                skills_str = skills
            else:
                skills_str = None

            row = PastJob(
                title            = title,
                description      = entry.get("description"),
                category         = entry.get("category", "automation"),
                skills           = skills_str,
                budget           = entry.get("budget"),
                job_type         = entry.get("job_type"),
                experience_level = entry.get("experience_level"),
                outcome          = entry.get("outcome", "completed"),
                weight           = float(entry.get("weight", 1.0)),
                source           = entry.get("source", "yaml_import"),
                reference_url    = entry.get("reference_url"),
            )
            session.add(row)
            inserted += 1

        session.commit()
        print(f"[seeder] Done — inserted: {inserted}, skipped (already exist): {skipped}")


def count():
    ensure_tables()
    with SessionLocal() as session:
        rows = session.query(PastJob.category, PastJob.id).all()
    from collections import Counter
    cats = Counter(r.category for r in rows)
    print(f"\n[seeder] past_jobs row counts:")
    if not cats:
        print("  (empty)")
    for cat, n in sorted(cats.items()):
        print(f"  {cat:<18} {n}")
    print(f"  {'TOTAL':<18} {sum(cats.values())}\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="MERIDIAN past_jobs seeder")
    parser.add_argument("--reset", action="store_true", help="Delete all past_jobs before seeding")
    parser.add_argument("--count", action="store_true", help="Just print row counts per category")
    args = parser.parse_args()

    if args.count:
        count()
    else:
        seed(reset=args.reset)
        count()

from sqlalchemy import Column, Integer, String, Text, Float, DateTime
from sqlalchemy.ext.declarative import declarative_base
import datetime

Base = declarative_base()


class Job(Base):
    __tablename__ = "jobs"
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    job_id = Column(String, unique=True, index=True)
    title = Column(String)
    description = Column(Text)
    budget = Column(Float)
    skills = Column(Text)
    client = Column(String)
    posted_at = Column(DateTime, default=datetime.datetime.utcnow)
    # MERIDIAN scoring columns (nullable — NULL means not yet processed)
    meridian_score   = Column(Integer,  nullable=True)
    meridian_verdict = Column(String,   nullable=True)
    meridian_reasoning = Column(Text,   nullable=True)
    meridian_run_at  = Column(DateTime, nullable=True)


class PastJob(Base):
    """Reference corpus for MERIDIAN scoring."""
    __tablename__ = "past_jobs"
    id              = Column(Integer,  primary_key=True, autoincrement=True)
    title           = Column(String,   nullable=False)
    description     = Column(Text,     nullable=True)
    category        = Column(String,   nullable=False, index=True)
    skills          = Column(Text,     nullable=True)   # JSON list stored as text
    budget          = Column(Float,    nullable=True)
    job_type        = Column(String,   nullable=True)   # 'hourly' | 'fixed'
    experience_level= Column(String,   nullable=True)
    outcome         = Column(String,   nullable=True)   # won/completed/interested/passed/lost
    weight          = Column(Float,    default=1.0)
    source          = Column(String,   default="manual")
    reference_url   = Column(String,   nullable=True)
    created_at      = Column(DateTime, default=datetime.datetime.utcnow)


class MeridianCostLog(Base):
    """Per-cycle GPT cost log for WhatsApp finance reports."""
    __tablename__ = "meridian_cost_log"
    id              = Column(Integer,  primary_key=True, autoincrement=True)
    cycle_at        = Column(DateTime, default=datetime.datetime.utcnow)
    jobs_scored     = Column(Integer,  default=0)
    input_tokens    = Column(Integer,  default=0)
    output_tokens   = Column(Integer,  default=0)
    cost_usd        = Column(Float,    default=0.0)
    cost_pkr        = Column(Float,    default=0.0)
    session_total_pkr = Column(Float,  default=0.0)

# New model for BHW threads
class BHWThread(Base):
    __tablename__ = "bhw_threads"
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    link = Column(String, unique=True, index=True)
    title = Column(String)
    author = Column(String)
    posted = Column(String)
    full_description = Column(Text)
    budget = Column(String)
    requirements = Column(Text)
    deadline = Column(String)
    contact_info = Column(String)
    tags = Column(Text)
    post_content = Column(Text)
    replies_count = Column(Integer)
    views_count = Column(Integer)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    gemini_decision = Column(String)

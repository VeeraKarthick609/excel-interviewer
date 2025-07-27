# app/database/postgres_db.py

import psycopg2
from psycopg2 import pool
import json
from typing import Dict, Any
import logging
from datetime import datetime

from app.core.config import settings

# --- Configure Logging ---
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# --- Initialize PostgreSQL Connection Pool ---
try:
    # Using a SimpleConnectionPool is good practice for server-based applications.
    # It manages a pool of connections that can be reused, avoiding the overhead
    # of establishing a new connection for every database operation.
    pg_pool = psycopg2.pool.SimpleConnectionPool(
        minconn=1,
        maxconn=10,
        dsn=settings.postgres_dsn
    )
    logger.info("PostgreSQL connection pool created successfully.")
except psycopg2.OperationalError as e:
    logger.error(f"Could not connect to PostgreSQL database: {e}")
    pg_pool = None


def init_db():
    """
    Initializes the database by creating the 'interview_results' table
    if it does not already exist. This is safe to run on every app startup.
    """
    if not pg_pool:
        logger.error("Database not initialized because connection pool is unavailable.")
        return

    conn = None
    try:
        conn = pg_pool.getconn()
        with conn.cursor() as cur:
            cur.execute("""
                CREATE TABLE IF NOT EXISTS interview_results (
                    session_id TEXT PRIMARY KEY,
                    start_time TIMESTAMPTZ,
                    end_time TIMESTAMPTZ,
                    final_score REAL,
                    feedback_summary TEXT,
                    full_transcript JSONB
                );
            """)
            conn.commit()
            logger.info("Database initialized: 'interview_results' table is ready.")
    except psycopg2.Error as e:
        logger.error(f"Error during database initialization: {e}")
        if conn:
            conn.rollback()
    finally:
        if conn:
            pg_pool.putconn(conn)


def save_interview_report(session_state: Dict[str, Any]):
    """
    Saves the final report of a completed interview to the PostgreSQL database.
    """
    if not pg_pool:
        logger.error("Could not save report because connection pool is unavailable.")
        return

    # A simple calculation for a final score (e.g., average score)
    scores = [e.get('score', 0) for e in session_state.get('evaluations', [])]
    final_score = sum(scores) / len(scores) if scores else 0.0

    # A summary of feedback
    feedback_items = [e.get('feedback', '') for e in session_state.get('evaluations', [])]
    feedback_summary = "\n".join(f"- {fb}" for fb in feedback_items)
    
    conn = None
    try:
        conn = pg_pool.getconn()
        with conn.cursor() as cur:
            # Using parameterized queries (%s) is crucial to prevent SQL injection.
            sql = """
                INSERT INTO interview_results (session_id, start_time, end_time, final_score, feedback_summary, full_transcript)
                VALUES (%s, %s, %s, %s, %s, %s)
                ON CONFLICT (session_id) DO UPDATE SET
                    end_time = EXCLUDED.end_time,
                    final_score = EXCLUDED.final_score,
                    feedback_summary = EXCLUDED.feedback_summary,
                    full_transcript = EXCLUDED.full_transcript;
            """
            params = (
                session_state['session_id'],
                session_state.get('start_time'),
                datetime.now().astimezone(), # Use timezone-aware datetime for end_time
                final_score,
                feedback_summary,
                json.dumps(session_state) # Convert the entire state to a JSON string for the JSONB column
            )
            cur.execute(sql, params)
            conn.commit()
            logger.info(f"Successfully saved report for session_id: {session_state['session_id']}")
    except psycopg2.Error as e:
        logger.error(f"Error saving interview report for session {session_state.get('session_id')}: {e}")
        if conn:
            conn.rollback()
    finally:
        if conn:
            pg_pool.putconn(conn)
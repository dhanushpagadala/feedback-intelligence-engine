"""
load_to_sqlite.py
------------------
Loads tagged_reviews.csv into a SQLite warehouse following schema.sql.
SQLite stands in for Postgres/Snowflake here -- swap the connection
string for a real driver (psycopg2, snowflake-connector-python) and
the schema/queries are unchanged.
"""

import csv
import sqlite3

DB_PATH = "/home/claude/feedback-intel/warehouse/feedback.db"
SCHEMA_PATH = "/home/claude/feedback-intel/warehouse/schema.sql"
CSV_PATH = "/home/claude/feedback-intel/llm_tagging/tagged_reviews.csv"


def main():
    conn = sqlite3.connect(DB_PATH)
    with open(SCHEMA_PATH) as f:
        conn.executescript(f.read())

    with open(CSV_PATH, newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))

    conn.executemany(
        "INSERT OR REPLACE INTO feedback (review_id, created_at, source, product, raw_text) "
        "VALUES (:review_id, :created_at, :source, :product, :raw_text)",
        rows,
    )
    conn.executemany(
        "INSERT OR REPLACE INTO feedback_tags (review_id, sentiment, root_cause, urgency, summary) "
        "VALUES (:review_id, :sentiment, :root_cause, :urgency, :summary)",
        rows,
    )
    conn.commit()

    n = conn.execute("SELECT COUNT(*) FROM feedback").fetchone()[0]
    print(f"Loaded {n} rows into {DB_PATH}")
    conn.close()


if __name__ == "__main__":
    main()

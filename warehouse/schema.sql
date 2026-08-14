-- schema.sql
-- Structured warehouse for LLM-tagged customer feedback.
-- Portable ANSI-ish SQL; tested against SQLite in this repo, but the
-- same DDL runs on Postgres/Snowflake with trivial type tweaks
-- (TEXT -> VARCHAR, no AUTOINCREMENT needed, etc).

CREATE TABLE IF NOT EXISTS feedback (
    review_id       TEXT PRIMARY KEY,
    created_at      TIMESTAMP NOT NULL,
    source          TEXT NOT NULL,          -- 'review' | 'ticket'
    product         TEXT NOT NULL,
    raw_text        TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS feedback_tags (
    review_id       TEXT PRIMARY KEY REFERENCES feedback(review_id),
    sentiment       TEXT NOT NULL,          -- positive | neutral | negative
    root_cause      TEXT NOT NULL,          -- billing | reliability | ...
    urgency         TEXT NOT NULL,          -- low | medium | high
    summary         TEXT,
    tagged_at       TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_feedback_created_at ON feedback(created_at);
CREATE INDEX IF NOT EXISTS idx_tags_root_cause ON feedback_tags(root_cause);
CREATE INDEX IF NOT EXISTS idx_tags_urgency ON feedback_tags(urgency);

-- Convenience view joining raw text + tags, since almost every
-- downstream query needs both.
CREATE VIEW IF NOT EXISTS v_feedback_enriched AS
SELECT
    f.review_id,
    f.created_at,
    f.source,
    f.product,
    f.raw_text,
    t.sentiment,
    t.root_cause,
    t.urgency,
    t.summary
FROM feedback f
JOIN feedback_tags t ON f.review_id = t.review_id;

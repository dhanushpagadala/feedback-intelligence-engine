-- analysis_queries.sql
-- Trend & anomaly-detection queries over the LLM-tagged feedback warehouse.

-- 1. Daily volume by root cause -- the base signal everything else builds on.
SELECT
    DATE(created_at)   AS day,
    root_cause,
    COUNT(*)            AS n
FROM v_feedback_enriched
GROUP BY day, root_cause
ORDER BY day;

-- 2. Root-cause mix overall (what to prioritize).
SELECT
    root_cause,
    COUNT(*) AS total,
    SUM(CASE WHEN urgency = 'high' THEN 1 ELSE 0 END) AS high_urgency_count,
    ROUND(100.0 * SUM(CASE WHEN sentiment = 'negative' THEN 1 ELSE 0 END) / COUNT(*), 1) AS pct_negative
FROM v_feedback_enriched
GROUP BY root_cause
ORDER BY total DESC;

-- 3. ANOMALY DETECTION: flag root causes whose volume in the last 48
--    hours is a statistical outlier vs. their own trailing baseline.
--    Method: z-score of (last-48h daily rate) vs the mean/stddev of
--    daily counts over the prior 30 days for that same root cause.
--    A z-score > 2 flags a cluster worth human attention -- this is
--    the query that would page an analyst instead of them noticing
--    two weeks later in a monthly report.
WITH daily_counts AS (
    SELECT
        root_cause,
        DATE(created_at) AS day,
        COUNT(*) AS n
    FROM v_feedback_enriched
    GROUP BY root_cause, day
),
baseline AS (
    -- trailing 30-day window, excluding the most recent 2 days so the
    -- spike doesn't get averaged into its own baseline
    SELECT
        root_cause,
        AVG(n) AS mean_n,
        -- population stddev, computed manually for SQLite portability
        SQRT(AVG(n * n) - AVG(n) * AVG(n)) AS stddev_n
    FROM daily_counts
    WHERE day < DATE('now', '-2 day')
      AND day >= DATE('now', '-32 day')
    GROUP BY root_cause
),
recent AS (
    SELECT
        root_cause,
        COUNT(*) AS n_last_48h
    FROM v_feedback_enriched
    WHERE created_at >= DATETIME('now', '-48 hours')
    GROUP BY root_cause
)
SELECT
    r.root_cause,
    r.n_last_48h,
    ROUND(b.mean_n, 2)                                   AS baseline_daily_mean,
    ROUND(b.stddev_n, 2)                                 AS baseline_daily_stddev,
    ROUND((r.n_last_48h / 2.0 - b.mean_n) /
          NULLIF(b.stddev_n, 0), 2)                      AS z_score,
    CASE
        WHEN (r.n_last_48h / 2.0 - b.mean_n) / NULLIF(b.stddev_n, 0) > 2
        THEN 'ANOMALY - investigate'
        ELSE 'normal'
    END AS flag
FROM recent r
JOIN baseline b ON r.root_cause = b.root_cause
ORDER BY z_score DESC;

-- 4. Urgency-weighted "pain score" per root cause over the last 7 days
--    -- useful for a single ranked list of what to fix first.
SELECT
    root_cause,
    COUNT(*) AS n,
    SUM(CASE urgency WHEN 'high' THEN 3 WHEN 'medium' THEN 2 ELSE 1 END) AS pain_score
FROM v_feedback_enriched
WHERE created_at >= DATETIME('now', '-7 days')
GROUP BY root_cause
ORDER BY pain_score DESC;

"""
generate_reviews.py
--------------------
Generates a synthetic, unstructured customer feedback dataset
(reviews + support tickets) for a fictional SaaS product ("Nimbus").

Why synthetic: lets the whole pipeline (tagging -> warehouse -> trend
detection -> dashboard) run end-to-end without needing a real dataset
or network access. Swap this out for a real CSV/API pull and the rest
of the pipeline is unchanged.

Design choice: we deliberately inject a *complaint cluster* (a spike
of billing-related, high-urgency tickets in the last 3 days) so the
anomaly-detection SQL query later has something real to catch.
"""

import csv
import random
from datetime import datetime, timedelta

random.seed(42)

PRODUCT = "Nimbus"

# Each template is tagged with its *ground truth* so we can later
# validate the LLM tagger's accuracy against something.
TEMPLATES = [
    # (text, sentiment, root_cause, urgency, source)
    ("{product} crashed twice while I was exporting my report. Lost all my work.", "negative", "reliability", "high", "review"),
    ("Support took 4 days to respond to my ticket about login failures.", "negative", "support_responsiveness", "medium", "ticket"),
    ("I was charged twice this month for the same subscription. Please fix this ASAP.", "negative", "billing", "high", "ticket"),
    ("The new dashboard redesign is confusing, I can't find the export button anymore.", "negative", "ui_ux", "low", "review"),
    ("Integration with Salesforce keeps failing silently, no error message at all.", "negative", "integration", "medium", "ticket"),
    ("Love the new analytics view, saved me hours every week!", "positive", "feature_praise", "low", "review"),
    ("Great customer support, resolved my issue in minutes.", "positive", "support_responsiveness", "low", "review"),
    ("App is fine but a bit slow when loading large datasets.", "neutral", "performance", "low", "review"),
    ("Why was I billed $49 when my plan is supposed to be $29? This is the second time.", "negative", "billing", "high", "ticket"),
    ("My invoice shows a charge from a plan I cancelled 3 months ago.", "negative", "billing", "high", "ticket"),
    ("Onboarding was smooth, docs are clear.", "positive", "onboarding", "low", "review"),
    ("Can't reset my password, the reset link goes to a 404 page.", "negative", "reliability", "high", "ticket"),
    ("Feature request: would love dark mode support.", "neutral", "feature_request", "low", "review"),
    ("Billing page says I owe $0 but I keep getting overdue emails. Very confusing.", "negative", "billing", "medium", "ticket"),
    ("Excellent product, exactly what our team needed.", "positive", "feature_praise", "low", "review"),
    ("Export to PDF has been broken for a week now, tried on 3 different browsers.", "negative", "reliability", "high", "ticket"),
    ("The mobile app logs me out every few minutes, very annoying.", "negative", "reliability", "medium", "ticket"),
    ("Pricing page is unclear about what's included in the Pro tier.", "neutral", "billing", "low", "review"),
    ("I was auto-upgraded to a paid plan without consent and charged $99.", "negative", "billing", "high", "ticket"),
    ("Slack integration stopped posting notifications after the last update.", "negative", "integration", "medium", "ticket"),
    ("Just wanted to say the new API docs are fantastic.", "positive", "feature_praise", "low", "review"),
    ("Getting double-charged is unacceptable, I want a refund and an explanation.", "negative", "billing", "high", "ticket"),
    ("UI feels cluttered after the redesign, too many nested menus.", "negative", "ui_ux", "low", "review"),
    ("Load times have gotten noticeably worse over the past month.", "negative", "performance", "medium", "review"),
    ("Great value for the price, recommend to anyone on the fence.", "positive", "feature_praise", "low", "review"),
]

# Indices of billing-related, high-urgency templates used to build the
# anomaly spike (simulating e.g. a botched pricing migration).
BILLING_SPIKE_IDX = [2, 8, 9, 13, 18, 21]

N_BACKGROUND = 170          # steady-state volume over the period
N_SPIKE = 34                # extra billing complaints in the last 3 days
DAYS_BACK = 45

def make_row(i, dt, forced_idx=None):
    idx = forced_idx if forced_idx is not None else random.randrange(len(TEMPLATES))
    text, sentiment, root_cause, urgency, source = TEMPLATES[idx]
    return {
        "review_id": f"FB-{i:05d}",
        "created_at": dt.strftime("%Y-%m-%d %H:%M:%S"),
        "source": source,
        "product": PRODUCT,
        "raw_text": text,
        # ground-truth labels, kept ONLY for validating the tagger later
        "_true_sentiment": sentiment,
        "_true_root_cause": root_cause,
        "_true_urgency": urgency,
    }

def main():
    rows = []
    now = datetime.now()
    start = now - timedelta(days=DAYS_BACK)

    # Background traffic, spread evenly across the whole window
    for i in range(N_BACKGROUND):
        dt = start + timedelta(seconds=random.randint(0, DAYS_BACK * 86400))
        rows.append(make_row(i, dt))

    # Injected anomaly: billing complaints clustered in the last 3 days
    for j in range(N_SPIKE):
        dt = now - timedelta(seconds=random.randint(0, 3 * 86400))
        idx = random.choice(BILLING_SPIKE_IDX)
        rows.append(make_row(N_BACKGROUND + j, dt, forced_idx=idx))

    rows.sort(key=lambda r: r["created_at"])

    out_path = "/home/claude/feedback-intel/data/raw_reviews.csv"
    with open(out_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)

    print(f"Wrote {len(rows)} rows to {out_path}")
    print(f"  background: {N_BACKGROUND}, injected billing spike: {N_SPIKE}")

if __name__ == "__main__":
    main()

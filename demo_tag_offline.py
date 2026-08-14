"""
demo_tag_offline.py
--------------------
This sandbox has no network access, so tag_reviews.py (the real Claude
API caller) can't actually reach api.anthropic.com from here.

This script produces the SAME output shape as tag_reviews.py, but by
using the ground-truth labels baked into the synthetic dataset (the
_true_* columns) instead of a live API call -- i.e. it's a stand-in
for "what Claude would return," not a different classification method.

Run tag_reviews.py instead of this script against real data.
"""

import csv

IN_PATH = "/home/claude/feedback-intel/data/raw_reviews.csv"
OUT_PATH = "/home/claude/feedback-intel/llm_tagging/tagged_reviews.csv"

SUMMARY_TEMPLATES = {
    "billing": "Customer reports an unexpected or incorrect charge.",
    "reliability": "Core functionality is broken or crashing for the user.",
    "performance": "User reports slowness or degraded speed.",
    "ui_ux": "User finds the interface confusing or hard to navigate.",
    "integration": "A third-party integration is failing or misbehaving.",
    "support_responsiveness": "User is commenting on support response time or quality.",
    "onboarding": "Feedback relates to the getting-started experience.",
    "feature_request": "User is requesting a new capability.",
    "feature_praise": "User is praising an existing feature.",
    "other": "General feedback not tied to a specific category.",
}

def main():
    with open(IN_PATH, newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))

    tagged = []
    for r in rows:
        sentiment = r["_true_sentiment"]
        root_cause = r["_true_root_cause"]
        urgency = r["_true_urgency"]
        tagged.append({
            "review_id": r["review_id"],
            "created_at": r["created_at"],
            "source": r["source"],
            "product": r["product"],
            "raw_text": r["raw_text"],
            "sentiment": sentiment,
            "root_cause": root_cause,
            "urgency": urgency,
            "summary": SUMMARY_TEMPLATES.get(root_cause, "General feedback."),
        })

    with open(OUT_PATH, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(tagged[0].keys()))
        writer.writeheader()
        writer.writerows(tagged)

    print(f"Wrote {len(tagged)} tagged rows to {OUT_PATH}")

if __name__ == "__main__":
    main()

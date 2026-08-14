"""
tag_reviews.py
--------------
Production tagging module: sends each raw review/ticket to Claude and
gets back a structured zero-shot classification (no training data,
no labeled examples needed -- just a well-specified schema).

Usage:
    export ANTHROPIC_API_KEY=sk-ant-...
    python3 tag_reviews.py --in ../data/raw_reviews.csv --out tagged_reviews.csv

Design notes (why this beats a regex/keyword NLP pipeline):
  - Regex tagging breaks the moment phrasing shifts ("billed twice" vs
    "double-charged" vs "charged again"). The LLM generalizes across
    phrasing without new rules per synonym.
  - Root-cause and urgency are judgment calls, not keyword matches --
    "I was auto-upgraded without consent" implies billing + high
    urgency even with zero shared vocabulary with "double charged".
  - Batching + strict JSON schema keeps cost and latency predictable
    and keeps the output machine-parseable for the SQL warehouse.
"""

import argparse
import csv
import json
import os
import sys
import time
import urllib.request

MODEL = "claude-sonnet-4-6"
API_URL = "https://api.anthropic.com/v1/messages"

ALLOWED_SENTIMENT = {"positive", "neutral", "negative"}
ALLOWED_ROOT_CAUSE = {
    "billing", "reliability", "performance", "ui_ux",
    "integration", "support_responsiveness", "onboarding",
    "feature_request", "feature_praise", "other",
}
ALLOWED_URGENCY = {"low", "medium", "high"}

SYSTEM_PROMPT = f"""You are a customer-feedback classification engine.
For each piece of feedback, return a JSON object with exactly these fields:
- sentiment: one of {sorted(ALLOWED_SENTIMENT)}
- root_cause: one of {sorted(ALLOWED_ROOT_CAUSE)}
- urgency: one of {sorted(ALLOWED_URGENCY)} (high = churn risk, money, or
  broken core functionality; medium = degraded experience; low = cosmetic
  or a feature request)
- summary: a single sentence (<15 words) restating the issue in your own words

Return ONLY a JSON array of objects, one per input item, in the same order.
No prose, no markdown fences, nothing else."""


def call_claude_batch(items, api_key):
    """items: list of {"review_id": ..., "raw_text": ...}"""
    user_content = "Classify these feedback items:\n\n" + "\n".join(
        f'{i+1}. [{it["review_id"]}] {it["raw_text"]}' for i, it in enumerate(items)
    )
    body = json.dumps({
        "model": MODEL,
        "max_tokens": 2000,
        "system": SYSTEM_PROMPT,
        "messages": [{"role": "user", "content": user_content}],
    }).encode("utf-8")

    req = urllib.request.Request(
        API_URL,
        data=body,
        headers={
            "Content-Type": "application/json",
            "x-api-key": api_key,
            "anthropic-version": "2023-06-01",
        },
        method="POST",
    )
    with urllib.request.urlopen(req) as resp:
        data = json.loads(resp.read())

    text = "".join(b["text"] for b in data["content"] if b["type"] == "text")
    text = text.strip().removeprefix("```json").removeprefix("```").removesuffix("```").strip()
    return json.loads(text)


def validate(tag):
    return (
        tag.get("sentiment") in ALLOWED_SENTIMENT
        and tag.get("root_cause") in ALLOWED_ROOT_CAUSE
        and tag.get("urgency") in ALLOWED_URGENCY
    )


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--in", dest="infile", default="../data/raw_reviews.csv")
    ap.add_argument("--out", dest="outfile", default="tagged_reviews.csv")
    ap.add_argument("--batch-size", type=int, default=10)
    args = ap.parse_args()

    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        sys.exit("Set ANTHROPIC_API_KEY in your environment first.")

    with open(args.infile, newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))

    tagged = []
    for start in range(0, len(rows), args.batch_size):
        batch = rows[start:start + args.batch_size]
        results = call_claude_batch(
            [{"review_id": r["review_id"], "raw_text": r["raw_text"]} for r in batch],
            api_key,
        )
        for row, tag in zip(batch, results):
            if not validate(tag):
                tag = {"sentiment": "neutral", "root_cause": "other", "urgency": "low",
                        "summary": "(validation failed, defaulted)"}
            tagged.append({**row, **tag})
        print(f"Tagged {min(start + args.batch_size, len(rows))}/{len(rows)}")
        time.sleep(0.2)  # gentle on rate limits

    with open(args.outfile, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(tagged[0].keys()))
        writer.writeheader()
        writer.writerows(tagged)

    print(f"Wrote {len(tagged)} tagged rows to {args.outfile}")


if __name__ == "__main__":
    main()

"""Build the eval suites (JSONL) from public datasets + seeded synthesis.

Sources (all fetched via the free HuggingFace datasets-server rows API):
- classification: ag_news (World/Sports/Business/Sci-Tech), 200 items balanced
- routing:        Tobi-Bueck/customer-support-tickets, four queues
- moderation:     tweet_eval/hate (hate vs not_hate), 200 balanced
- agent_next_action: synthetic support-agent tool-selection scenarios, 200

Default builds cover routing (CC-BY-NC-4.0) and agent_next_action (MIT).
Classification and moderation require explicit --suite and --local-out outside
the repository, and use under their source terms. Sources are printed, not stored.

Usage: python scripts/build_datasets.py [--size 200] [--seed 42]
"""

from __future__ import annotations

import argparse
import json
import random
import sys
from pathlib import Path

import httpx

SRC_DATASETS = Path(__file__).resolve().parents[1] / "src" / "verdict_router" / "datasets"
REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
LOCAL_ONLY_SUITES = {"classification", "moderation"}
ROWS_URL = "https://datasets-server.huggingface.co/rows"
FIRST_ROWS_URL = "https://datasets-server.huggingface.co/first-rows"


def fetch_rows(dataset: str, config: str, split: str, n_pages: int, page_size: int = 100) -> list[dict]:
    """Fetch rows from spaced offsets so we cover the dataset rather than its head."""
    rows: list[dict] = []
    with httpx.Client(timeout=30.0, headers={"User-Agent": "verdict-bench/0.1"}) as client:
        # Discover split size from first-rows metadata (falls back to blind offsets).
        spread = [int(i * (15000 / max(1, n_pages - 1))) if n_pages > 1 else 0 for i in range(n_pages)]
        for offset in spread:
            resp = client.get(
                ROWS_URL,
                params={
                    "dataset": dataset,
                    "config": config,
                    "split": split,
                    "offset": offset,
                    "length": page_size,
                },
            )
            resp.raise_for_status()
            data = resp.json()
            rows.extend(data.get("rows", []))
    return rows


def fetch_label_names(dataset: str, config: str, split: str) -> list[str] | None:
    try:
        resp = httpx.get(
            FIRST_ROWS_URL,
            params={"dataset": dataset, "config": config, "split": split},
            timeout=30.0,
            headers={"User-Agent": "verdict-bench/0.1"},
        )
        resp.raise_for_status()
        for feature in resp.json().get("features", []):
            if feature.get("name") == "label" and feature.get("type", {}).get("_type") == "ClassLabel":
                return feature["type"]["names"]
    except (httpx.HTTPError, KeyError, ValueError):
        return None
    return None


def balanced_sample(rows: list[dict], labels: list[str], size: int, rng: random.Random) -> list[dict]:
    by_label: dict[str, list[dict]] = {}
    for r in rows:
        lbl = labels[r["row"]["label"]] if isinstance(r["row"]["label"], int) else str(r["row"]["label"])
        by_label.setdefault(lbl, []).append(r["row"])
    per = size // len(by_label)
    picked: list[dict] = []
    for lbl, bucket in by_label.items():
        rng.shuffle(bucket)
        picked.extend(bucket[:per])
    # top up if rounding left us short
    for lbl, bucket in by_label.items():
        while len(picked) < size and bucket[len(bucket) - 1]:
            extra = bucket[len(picked) % len(bucket)]
            if extra not in picked:
                picked.append(extra)
            else:
                break
        if len(picked) >= size:
            break
    return picked[:size]


def write_suite(name: str, items: list[dict], local_out: Path | None = None) -> None:
    if name in LOCAL_ONLY_SUITES:
        if local_out is None or local_out.resolve().is_relative_to(REPOSITORY_ROOT):
            raise ValueError("Local-only suites require --local-out outside the repository")
        destination = local_out
    else:
        destination = SRC_DATASETS
    destination.mkdir(parents=True, exist_ok=True)
    path = destination / f"{name}.jsonl"
    with path.open("w", encoding="utf-8") as fh:
        for item in items:
            fh.write(json.dumps(item, ensure_ascii=False) + "\n")
    print(f"[ok] {name}: {len(items)} items -> {path}")


# ---------------------------------------------------------------- classification

AG_LABELS = ["World", "Sports", "Business", "Sci/Tech"]


def build_classification(size: int, rng: random.Random) -> tuple[list[dict], str]:
    try:
        rows = fetch_rows("fancyzhx/ag_news", "default", "train", n_pages=8)
        label_names = fetch_label_names("fancyzhx/ag_news", "default", "train") or AG_LABELS
        picked = balanced_sample(rows, label_names, size, rng)
        items = [
            {
                "id": f"classif-{i:04d}",
                "question": "Which news category does this headline belong to?",
                "answers": AG_LABELS,
                "context": r["text"][:500],
                "expected": label_names[r["label"]] if isinstance(r["label"], int) else r["label"],
            }
            for i, r in enumerate(picked)
        ]
        if all(it["expected"] in AG_LABELS for it in items) and len(items) >= size * 0.9:
            return items, "ag_news (HuggingFace datasets-server)"
    except (httpx.HTTPError, KeyError, ValueError) as exc:
        print(f"[warn] ag_news fetch failed ({exc}); using synthetic headlines")
    return synthetic_classification(size, rng), "synthetic headlines (fallback)"


def synthetic_classification(size: int, rng: random.Random) -> list[dict]:
    templates = {
        "World": ["Talks collapse in {place} as leaders disagree", "Election results spark protests across {place}"],
        "Sports": ["{team} defeats {team2} {x}-{y} in overtime thriller", "Star quarterback signs record deal with {team}"],
        "Business": ["{corp} shares fall {x}% after earnings miss", "Merger talks between {corp} and {corp2} heat up"],
        "Sci/Tech": ["Researchers unveil quantum chip that beats {corp}'s benchmark", "New AI model from {corp} open-sourced"],
    }
    places, teams, corps = ["Geneva", "Osaka", "Nairobi", "Lima"], ["Ravens", "Tigers", "Comets", "Sharks"], ["AcmeCorp", "Globex", "Initech", "Umbra"]
    items = []
    labels = list(templates) * (size // 4)
    rng.shuffle(labels)
    for i, lbl in enumerate(labels):
        t = rng.choice(templates[lbl])
        text = t.format(place=rng.choice(places), team=rng.choice(teams), team2=rng.choice(teams), corp=rng.choice(corps), corp2=rng.choice(corps), x=rng.randint(2, 30), y=rng.randint(0, 3))
        items.append({"id": f"classif-{i:04d}", "question": "Which news category does this headline belong to?", "answers": AG_LABELS, "context": text, "expected": lbl})
    return items


# ---------------------------------------------------------------- routing

# Real support-ticket routing: Tobi-Bueck/customer-support-tickets has a `queue`
# column (subject+body -> team queue). PolyAI/banking77 is not exposed on the
# datasets-server viewer, so we use this instead.
ROUTING_DATASET = "Tobi-Bueck/customer-support-tickets"
ROUTING_TOP_QUEUES = 4


def build_routing(size: int, rng: random.Random) -> tuple[list[dict], str]:
    try:
        rows = fetch_rows(ROUTING_DATASET, "default", "train", n_pages=6)
        cleaned = []
        for r in rows:
            row = r["row"]
            if str(row.get("language", "en")).lower() != "en":
                continue
            subject = str(row.get("subject") or "").strip()
            body = str(row.get("body") or "").strip()
            queue = str(row.get("queue") or "").strip()
            if queue and (subject or body):
                cleaned.append({"text": f"{subject}\n{body}"[:600], "queue": queue})
        if len(cleaned) < size:
            raise ValueError(f"only {len(cleaned)} usable rows")
        counts: dict[str, int] = {}
        for r in cleaned:
            counts[r["queue"]] = counts.get(r["queue"], 0) + 1
        top = [q for q, _ in sorted(counts.items(), key=lambda kv: -kv[1])[:ROUTING_TOP_QUEUES]]
        by_queue: dict[str, list[dict]] = {q: [] for q in top}
        for r in cleaned:
            if r["queue"] in by_queue:
                by_queue[r["queue"]].append(r)
        per = size // len(top)
        items: list[dict] = []
        for q in top:
            rng.shuffle(by_queue[q])
            for r in by_queue[q][:per]:
                items.append(
                    {
                        "id": f"route-{len(items):04d}",
                        "question": "Which support team queue should handle this customer ticket?",
                        "answers": top,
                        "context": r["text"],
                        "expected": q,
                    }
                )
        if len(items) >= size * 0.9:
            return items, f"{ROUTING_DATASET} top-{len(top)} queues (HuggingFace datasets-server)"
        print(f"[warn] routing coverage thin ({len(items)} items); topping up synthetically")
    except (httpx.HTTPError, KeyError, ValueError) as exc:
        print(f"[warn] {ROUTING_DATASET} fetch failed ({exc}); using synthetic tickets")
    return synthetic_routing(size, rng), "synthetic tickets (fallback)"


def synthetic_routing(size: int, rng: random.Random) -> list[dict]:
    queues = ["Billing", "Technical", "Account", "Shipping"]
    templates = {
        "Billing": "I was charged twice this month and need one of the charges reversed.",
        "Technical": "The app crashes every time I try to export my data.",
        "Account": "How do I change the email address linked to my profile?",
        "Shipping": "My package has been stuck in transit for two weeks.",
    }
    items = []
    queues = list(templates) * (size // 4)
    rng.shuffle(queues)
    for i, q in enumerate(queues):
        items.append({"id": f"route-{i:04d}", "question": "Which support team queue should handle this customer ticket?", "answers": queues, "context": templates[q], "expected": q})
    return items


# ---------------------------------------------------------------- moderation

def build_moderation(size: int, rng: random.Random) -> tuple[list[dict], str]:
    answers = ["hate", "not_hate"]
    try:
        rows = fetch_rows("cardiffnlp/tweet_eval", "hate", "train", n_pages=4)
        label_names = fetch_label_names("cardiffnlp/tweet_eval", "hate", "train") or ["hate", "non-hate"]
        mapping = {"hate": "hate", "non_hate": "not_hate", "not_hate": "not_hate"}
        picked = balanced_sample(rows, label_names, size, rng)
        items = []
        for r in picked:
            expected = mapping.get(str(r["label"]).lower().replace("-", "_"), None)
            if isinstance(r["label"], int):
                expected = mapping.get(label_names[r["label"]].lower().replace("-", "_"), None)
            if expected is None:
                continue
            items.append(
                {
                    "id": f"mod-{len(items):04d}",
                    "question": "Does this text contain hate speech? Reply hate or not_hate.",
                    "answers": answers,
                    "context": r["text"][:400],
                    "expected": expected,
                }
            )
        if len(items) >= size * 0.8:
            return items, "tweet_eval/hate (HuggingFace datasets-server)"
    except (httpx.HTTPError, KeyError, ValueError) as exc:
        print(f"[warn] tweet_eval fetch failed ({exc}); using synthetic moderation items")
    return synthetic_moderation(size, rng), "synthetic comments (fallback)"


def synthetic_moderation(size: int, rng: random.Random) -> list[dict]:
    hateful = ["You people are vermin and should be expelled from this country.", "All {group} are animals, someone should deal with them."]
    fine = ["Just landed in Lisbon, the weather is unreal today!", "Can anyone recommend a good budgeting app for students?"]
    items = []
    labels = ["hate", "not_hate"] * (size // 2)
    rng.shuffle(labels)
    for i, lbl in enumerate(labels):
        pool = hateful if lbl == "hate" else fine
        text = rng.choice(pool).format(group="outsiders")
        items.append({"id": f"mod-{i:04d}", "question": "Does this text contain hate speech? Reply hate or not_hate.", "answers": ["hate", "not_hate"], "context": text, "expected": lbl})
    return items


# ------------------------------------------------------- agent next action

TOOLS = [
    "lookup_order",
    "issue_refund",
    "check_payment_status",
    "escalate_to_human",
    "send_faq_link",
    "update_shipping_address",
]

AGENT_TEMPLATES = {
    "lookup_order": [
        "I placed order {oid} two weeks ago and it still shows 'processing'. Where is it?",
        "Can you check what happened with order {oid}? The tracking page is empty.",
    ],
    "issue_refund": [
        "The {product} arrived with a cracked screen. I want my money back.",
        "This {product} is not what I ordered at all. Please refund order {oid}.",
    ],
    "check_payment_status": [
        "Did the payment for order {oid} actually go through? My card shows pending.",
        "Can you confirm if my last payment was processed? Nothing moved in my bank app.",
    ],
    "escalate_to_human": [
        "Third time I'm writing about this. Get me a real person on the phone NOW.",
        "Your bot has failed me twice today. I demand to speak with a human supervisor.",
    ],
    "send_faq_link": [
        "How do I change the notification settings in the app?",
        "Where can I find your returns policy? Just point me to the info.",
    ],
    "update_shipping_address": [
        "I'm moving next week, please send order {oid} to my new place instead.",
        "Wrong apartment number on order {oid}! Please update the delivery address.",
    ],
}


def build_agent(size: int, rng: random.Random) -> tuple[list[dict], str]:
    products = ["blender", "wireless keyboard", "desk lamp", "espresso machine", "phone case"]
    items = []
    labels = list(AGENT_TEMPLATES) * (size // len(AGENT_TEMPLATES) + 1)
    labels = labels[:size]
    rng.shuffle(labels)
    for i, tool in enumerate(labels):
        msg = rng.choice(AGENT_TEMPLATES[tool]).format(oid=f"#{rng.randint(10000, 99999)}", product=rng.choice(products))
        items.append(
            {
                "id": f"agent-{i:04d}",
                "question": "You are a customer-support agent. Which single tool should you call next?",
                "answers": TOOLS,
                "context": f"Available tools: {json.dumps(TOOLS)}\nCustomer message: \"{msg}\"",
                "expected": tool,
            }
        )
    return items, "synthetic tool-selection scenarios (seeded)"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--size", type=int, default=200, help="items per suite")
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument(
        "--suite", action="append",
        choices=["classification", "routing", "moderation", "agent_next_action"],
    )
    parser.add_argument("--local-out", type=Path, help="private output directory outside this repository")
    args = parser.parse_args()
    selected_suites = args.suite or ["routing", "agent_next_action"]
    if LOCAL_ONLY_SUITES.intersection(selected_suites) and (
        args.local_out is None or args.local_out.resolve().is_relative_to(REPOSITORY_ROOT)
    ):
        parser.error(
            "Local-only suites require --local-out outside the repository; "
            "review DATASET_NOTICE.md first"
        )
    rng = random.Random(args.seed)

    builders = [
        ("classification", build_classification),
        ("routing", build_routing),
        ("moderation", build_moderation),
        ("agent_next_action", build_agent),
    ]
    failed = []
    for name, builder in builders:
        if name not in selected_suites:
            continue
        try:
            items, source = builder(args.size, rng)
            write_suite(name, items, args.local_out)
            print(f"     source: {source}")
        except Exception as exc:  # noqa: BLE001 - never die mid-build overnight
            print(f"[fail] {name}: {type(exc).__name__}: {exc}")
            failed.append(name)
    if failed:
        print(f"suites failed to build: {failed}")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())

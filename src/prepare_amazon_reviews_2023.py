from __future__ import annotations

import argparse
import gzip
import hashlib
import io
import json
import random
import urllib.request
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
RAW_DIR = ROOT / "data" / "raw"
RANDOM_SEED = 42

BASE_URL = "https://huggingface.co/datasets/McAuley-Lab/Amazon-Reviews-2023/resolve/main/raw"
DEFAULT_CATEGORY = "All_Beauty"

REGIONS = ["North", "South", "East", "West", "Central"]
AGE_GROUPS = ["18-24", "25-34", "35-44", "45-54", "55+"]
CHANNELS = ["Paid Search", "Organic", "Social", "Referral", "Email"]


def is_gzip_source(source: str | Path) -> bool:
    return str(source).lower().endswith(".gz")


def iter_jsonl(source: str | Path):
    if isinstance(source, Path):
        opener = gzip.open if is_gzip_source(source) else open
        with opener(source, "rt", encoding="utf-8") as file:
            for line in file:
                if line.strip():
                    yield json.loads(line)
        return

    print(f"Streaming {source}")
    with urllib.request.urlopen(source) as response:
        stream = gzip.GzipFile(fileobj=response) if is_gzip_source(source) else response
        text_stream = io.TextIOWrapper(stream, encoding="utf-8")
        for line in text_stream:
            if line.strip():
                yield json.loads(line)


def clean_price(value: Any) -> float | None:
    if value is None or value == "":
        return None
    if isinstance(value, (int, float)):
        return float(value)
    value = str(value).replace("$", "").replace(",", "").strip()
    try:
        return float(value)
    except ValueError:
        return None


def timestamp_to_date(record: dict[str, Any]) -> date:
    raw_timestamp = record.get("timestamp") or record.get("sort_timestamp")
    if not raw_timestamp:
        return date(2023, 1, 1) + timedelta(days=random.randint(0, 270))

    timestamp = int(raw_timestamp)
    if timestamp > 10_000_000_000:
        timestamp = timestamp / 1000
    return datetime.utcfromtimestamp(timestamp).date()


def infer_topic(text: str) -> str:
    lowered = text.lower()
    topic_keywords = {
        "quality": ["quality", "broken", "cheap", "durable", "material", "defective"],
        "delivery": ["delivery", "shipping", "package", "arrived", "late"],
        "price": ["price", "value", "money", "expensive", "worth"],
        "usability": ["easy", "use", "setup", "install", "works"],
        "appearance": ["color", "look", "design", "beautiful", "size"],
        "performance": ["battery", "last", "performance", "effective", "results"],
    }
    for topic, keywords in topic_keywords.items():
        if any(keyword in lowered for keyword in keywords):
            return topic
    return "general"


def load_metadata(meta_source: str | Path, max_meta_rows: int, wanted_product_ids: set[str]) -> dict[str, dict[str, Any]]:
    metadata: dict[str, dict[str, Any]] = {}
    for index, record in enumerate(iter_jsonl(meta_source), start=1):
        parent_asin = record.get("parent_asin")
        if parent_asin and parent_asin in wanted_product_ids:
            metadata[parent_asin] = {
                "product_name": record.get("title") or parent_asin,
                "category": record.get("main_category") or "Unknown",
                "price": clean_price(record.get("price")),
            }
        if wanted_product_ids and wanted_product_ids.issubset(metadata):
            break
        if index >= max_meta_rows:
            break
    return metadata


def load_reviews(review_source: str | Path, sample_size: int) -> list[dict[str, Any]]:
    rows = []
    for record in iter_jsonl(review_source):
        text = str(record.get("text") or "").strip()
        rating = record.get("rating")
        user_id = record.get("user_id")
        product_id = record.get("parent_asin") or record.get("asin")

        if text and rating and user_id and product_id:
            rows.append(record)
        if len(rows) >= sample_size:
            break

    return rows


def build_portfolio_tables(records: list[dict[str, Any]], metadata: dict[str, dict[str, Any]]) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    customers = []
    orders = []
    reviews = []
    seen_customers = set()

    for idx, record in enumerate(records, start=1):
        raw_user_id = record["user_id"]
        customer_hash = int(hashlib.sha1(raw_user_id.encode("utf-8")).hexdigest()[:10], 16)
        customer_id = f"C_{customer_hash % 10_000_000:07d}"
        product_id = record.get("parent_asin") or record.get("asin")
        product_meta = metadata.get(product_id, {})
        review_date = timestamp_to_date(record)

        if customer_id not in seen_customers:
            customers.append(
                {
                    "customer_id": customer_id,
                    "source_user_id": raw_user_id,
                    "signup_date": (review_date - timedelta(days=random.randint(30, 720))).isoformat(),
                    "region": random.choice(REGIONS),
                    "age_group": random.choices(AGE_GROUPS, weights=[0.18, 0.32, 0.24, 0.16, 0.10])[0],
                    "acquisition_channel": random.choices(CHANNELS, weights=[0.25, 0.28, 0.20, 0.15, 0.12])[0],
                }
            )
            seen_customers.add(customer_id)

        price = product_meta.get("price")
        if price is None or price <= 0:
            price = round(float(np.random.lognormal(mean=3.1, sigma=0.65)), 2)

        rating = int(round(float(record["rating"])))
        discount_pct = round(max(0, np.random.normal(0.08, 0.07)), 2)
        order_value = round(price * (1 - min(discount_pct, 0.35)) * np.random.normal(1.0, 0.06), 2)
        ab_group = random.choice(["control", "treatment"])

        base_conversion = 0.48 + (0.05 if rating >= 4 else -0.04 if rating <= 2 else 0)
        treatment_lift = 0.05 if ab_group == "treatment" else 0
        converted = int(random.random() < min(max(base_conversion + treatment_lift, 0.05), 0.95))
        retained_30d = int(random.random() < min(max(0.30 + treatment_lift + ((rating - 3) * 0.04), 0.05), 0.90))
        is_returned = int(random.random() < min(max(0.08 + ((3 - rating) * 0.04), 0.02), 0.45))

        order_id = f"O{idx:06d}"
        orders.append(
            {
                "order_id": order_id,
                "customer_id": customer_id,
                "order_date": review_date.isoformat(),
                "product_id": product_id,
                "product_name": product_meta.get("product_name") or product_id,
                "category": product_meta.get("category") or "Amazon Reviews 2023",
                "order_value": order_value,
                "discount_pct": discount_pct,
                "is_returned": is_returned,
                "ab_group": ab_group,
                "converted": converted,
                "retained_30d": retained_30d,
            }
        )

        review_title = str(record.get("title") or "").strip()
        review_text = str(record.get("text") or "").strip()
        reviews.append(
            {
                "review_id": f"R{idx:06d}",
                "order_id": order_id,
                "customer_id": customer_id,
                "review_date": review_date.isoformat(),
                "rating": rating,
                "review_title": review_title,
                "review_text": review_text,
                "review_topic": infer_topic(f"{review_title} {review_text}"),
                "verified_purchase": bool(record.get("verified_purchase", False)),
                "helpful_votes": int(record.get("helpful_vote") or record.get("helpful_votes") or 0),
                "source_product_id": product_id,
            }
        )

    return pd.DataFrame(customers), pd.DataFrame(orders), pd.DataFrame(reviews)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Prepare a sampled Amazon Reviews 2023 dataset for this portfolio project.")
    parser.add_argument("--category", default=DEFAULT_CATEGORY, help="Amazon Reviews 2023 category, for example All_Beauty.")
    parser.add_argument("--sample-size", type=int, default=5000, help="Number of real review rows to convert.")
    parser.add_argument("--max-meta-rows", type=int, default=200000, help="Maximum metadata rows to scan.")
    parser.add_argument("--review-file", type=Path, help="Optional local .jsonl or .jsonl.gz review file.")
    parser.add_argument("--meta-file", type=Path, help="Optional local .jsonl or .jsonl.gz metadata file.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    random.seed(RANDOM_SEED)
    np.random.seed(RANDOM_SEED)

    review_url = f"{BASE_URL}/review_categories/{args.category}.jsonl"
    meta_url = f"{BASE_URL}/meta_categories/meta_{args.category}.jsonl"
    review_source = args.review_file or review_url
    meta_source = args.meta_file or meta_url

    records = load_reviews(review_source, args.sample_size)
    product_ids = {str(record.get("parent_asin") or record.get("asin")) for record in records}
    metadata = load_metadata(meta_source, args.max_meta_rows, product_ids)
    customers, orders, reviews = build_portfolio_tables(records, metadata)

    RAW_DIR.mkdir(parents=True, exist_ok=True)
    customers.to_csv(RAW_DIR / "customers.csv", index=False)
    orders.to_csv(RAW_DIR / "orders.csv", index=False)
    reviews.to_csv(RAW_DIR / "product_reviews.csv", index=False)

    print(
        "Prepared Amazon Reviews 2023 sample: "
        f"{len(customers)} customers, {len(orders)} simulated orders, {len(reviews)} real reviews."
    )
    print("Note: A/B test, order value, return, demographic, and acquisition fields are simulated.")


if __name__ == "__main__":
    main()

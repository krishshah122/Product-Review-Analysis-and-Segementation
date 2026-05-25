from __future__ import annotations

import random
from datetime import date, timedelta
from pathlib import Path

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
RAW_DIR = ROOT / "data" / "raw"
RANDOM_SEED = 42


PRODUCTS = [
    ("P001", "AeroFit Smartwatch", "Wearables", 129.99),
    ("P002", "PulseBeat Earbuds", "Audio", 79.99),
    ("P003", "HydraMax Bottle", "Lifestyle", 24.99),
    ("P004", "VoltCharge Power Bank", "Electronics", 49.99),
    ("P005", "Lumina Desk Lamp", "Home Office", 39.99),
    ("P006", "BreezeAir Mini Fan", "Home Office", 34.99),
    ("P007", "CoreFlex Yoga Mat", "Fitness", 44.99),
    ("P008", "SnapChef Blender", "Kitchen", 89.99),
    ("P009", "ZenRest Pillow", "Home", 59.99),
    ("P010", "FocusPro Webcam", "Electronics", 69.99),
]

POSITIVE_PHRASES = [
    "excellent quality and very easy to use",
    "battery life is better than expected",
    "fast delivery and the product feels premium",
    "great value for money and works perfectly",
    "customer support solved my issue quickly",
    "design is clean and performance is reliable",
]

NEGATIVE_PHRASES = [
    "stopped working after a few days",
    "battery drains too quickly",
    "delivery was late and packaging was damaged",
    "quality feels cheap for the price",
    "customer support took too long to respond",
    "setup was confusing and the app kept crashing",
]

NEUTRAL_PHRASES = [
    "works as described with no major issues",
    "product is okay for daily use",
    "shipping was normal and setup was simple",
    "quality is average but acceptable",
    "does the job but nothing special",
]

TOPICS = {
    "battery": ["battery life", "charging", "power"],
    "delivery": ["delivery", "shipping", "packaging"],
    "quality": ["quality", "durability", "material"],
    "support": ["support", "service", "response"],
    "usability": ["setup", "app", "easy"],
    "price": ["price", "value", "money"],
}


def random_date(start: date, end: date) -> date:
    return start + timedelta(days=random.randint(0, (end - start).days))


def choose_review(rating: int) -> tuple[str, str]:
    if rating >= 4:
        text = random.choice(POSITIVE_PHRASES)
    elif rating <= 2:
        text = random.choice(NEGATIVE_PHRASES)
    else:
        text = random.choice(NEUTRAL_PHRASES)

    topic = next(
        (topic for topic, keywords in TOPICS.items() if any(keyword in text for keyword in keywords)),
        random.choice(list(TOPICS)),
    )
    return text, topic


def build_customers(n_customers: int = 750) -> pd.DataFrame:
    signup_start = date(2024, 1, 1)
    signup_end = date(2025, 12, 31)
    regions = ["North", "South", "East", "West", "Central"]
    age_groups = ["18-24", "25-34", "35-44", "45-54", "55+"]
    channels = ["Paid Search", "Organic", "Social", "Referral", "Email"]

    rows = []
    for i in range(1, n_customers + 1):
        rows.append(
            {
                "customer_id": f"C{i:04d}",
                "signup_date": random_date(signup_start, signup_end).isoformat(),
                "region": random.choice(regions),
                "age_group": random.choices(age_groups, weights=[0.18, 0.32, 0.24, 0.16, 0.10])[0],
                "acquisition_channel": random.choices(channels, weights=[0.25, 0.28, 0.20, 0.15, 0.12])[0],
            }
        )
    return pd.DataFrame(rows)


def build_orders_and_reviews(customers: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    order_rows = []
    review_rows = []
    order_id = 1
    review_id = 1
    order_start = date(2025, 1, 1)
    order_end = date(2025, 12, 31)

    for customer in customers.itertuples(index=False):
        order_count = np.random.choice([1, 2, 3, 4, 5, 6], p=[0.38, 0.25, 0.17, 0.10, 0.06, 0.04])
        for _ in range(order_count):
            product_id, product_name, category, base_price = random.choice(PRODUCTS)
            order_date = random_date(order_start, order_end)
            discount_pct = round(max(0, np.random.normal(0.10, 0.08)), 2)
            order_value = round(base_price * (1 - min(discount_pct, 0.35)) * np.random.normal(1.0, 0.08), 2)
            ab_group = random.choice(["control", "treatment"])

            treatment_lift = 0.06 if ab_group == "treatment" else 0
            converted = int(random.random() < (0.54 + treatment_lift))
            retained_30d = int(random.random() < (0.33 + (0.04 if ab_group == "treatment" else 0)))

            product_risk = 0.10 if product_name in {"PulseBeat Earbuds", "SnapChef Blender"} else 0.03
            is_returned = int(random.random() < (0.08 + product_risk + max(discount_pct - 0.18, 0)))

            order_key = f"O{order_id:05d}"
            order_rows.append(
                {
                    "order_id": order_key,
                    "customer_id": customer.customer_id,
                    "order_date": order_date.isoformat(),
                    "product_id": product_id,
                    "product_name": product_name,
                    "category": category,
                    "order_value": order_value,
                    "discount_pct": discount_pct,
                    "is_returned": is_returned,
                    "ab_group": ab_group,
                    "converted": converted,
                    "retained_30d": retained_30d,
                }
            )

            rating_base = np.random.choice([1, 2, 3, 4, 5], p=[0.08, 0.12, 0.20, 0.34, 0.26])
            if is_returned:
                rating = max(1, rating_base - random.choice([1, 2]))
            elif product_name in {"AeroFit Smartwatch", "Lumina Desk Lamp"}:
                rating = min(5, rating_base + 1)
            else:
                rating = rating_base

            review_text, review_topic = choose_review(rating)
            review_rows.append(
                {
                    "review_id": f"R{review_id:05d}",
                    "order_id": order_key,
                    "customer_id": customer.customer_id,
                    "review_date": (order_date + timedelta(days=random.randint(1, 21))).isoformat(),
                    "rating": rating,
                    "review_text": review_text,
                    "review_topic": review_topic,
                }
            )

            order_id += 1
            review_id += 1

    return pd.DataFrame(order_rows), pd.DataFrame(review_rows)


def main() -> None:
    random.seed(RANDOM_SEED)
    np.random.seed(RANDOM_SEED)
    RAW_DIR.mkdir(parents=True, exist_ok=True)

    customers = build_customers()
    orders, reviews = build_orders_and_reviews(customers)

    customers.to_csv(RAW_DIR / "customers.csv", index=False)
    orders.to_csv(RAW_DIR / "orders.csv", index=False)
    reviews.to_csv(RAW_DIR / "product_reviews.csv", index=False)

    print(f"Generated {len(customers)} customers, {len(orders)} orders, and {len(reviews)} reviews.")


if __name__ == "__main__":
    main()

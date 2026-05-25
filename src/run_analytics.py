from __future__ import annotations

import math
import sqlite3
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
RAW_DIR = ROOT / "data" / "raw"
PROCESSED_DIR = ROOT / "data" / "processed"
REPORTS_DIR = ROOT / "reports"
SQL_DIR = ROOT / "sql"

POSITIVE_WORDS = {
    "amazing",
    "awesome",
    "beautiful",
    "best",
    "excellent",
    "easy",
    "better",
    "fast",
    "favorite",
    "good",
    "premium",
    "great",
    "love",
    "loved",
    "perfectly",
    "perfect",
    "quickly",
    "clean",
    "reliable",
    "recommend",
    "soft",
    "works",
    "worth",
}

NEGATIVE_WORDS = {
    "awful",
    "bad",
    "broke",
    "broken",
    "stopped",
    "drains",
    "late",
    "damaged",
    "cheap",
    "defective",
    "disappointed",
    "disappointing",
    "horrible",
    "long",
    "poor",
    "refund",
    "returned",
    "confusing",
    "crashing",
    "waste",
    "worst",
}


def sentiment_score(text: str, rating: int) -> tuple[str, float]:
    tokens = {token.strip(".,!?").lower() for token in text.split()}
    lexical_score = sum(token in POSITIVE_WORDS for token in tokens) - sum(token in NEGATIVE_WORDS for token in tokens)
    rating_score = (rating - 3) / 2
    score = max(-1.0, min(1.0, (lexical_score / 4) + rating_score))

    if score >= 0.25:
        label = "positive"
    elif score <= -0.25:
        label = "negative"
    else:
        label = "neutral"
    return label, round(score, 3)


def two_proportion_z_test(success_a: int, n_a: int, success_b: int, n_b: int) -> tuple[float, float]:
    p_a = success_a / n_a
    p_b = success_b / n_b
    pooled = (success_a + success_b) / (n_a + n_b)
    standard_error = math.sqrt(pooled * (1 - pooled) * ((1 / n_a) + (1 / n_b)))
    if standard_error == 0:
        return 0.0, 1.0

    z_score = (p_b - p_a) / standard_error
    p_value = math.erfc(abs(z_score) / math.sqrt(2))
    return round(z_score, 4), round(p_value, 4)


def load_data() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    customers = pd.read_csv(RAW_DIR / "customers.csv")
    orders = pd.read_csv(RAW_DIR / "orders.csv")
    reviews = pd.read_csv(RAW_DIR / "product_reviews.csv")

    for column in ["signup_date"]:
        customers[column] = pd.to_datetime(customers[column])
    for column in ["order_date"]:
        orders[column] = pd.to_datetime(orders[column])
    for column in ["review_date"]:
        reviews[column] = pd.to_datetime(reviews[column])

    scored = reviews.apply(lambda row: sentiment_score(row["review_text"], row["rating"]), axis=1)
    reviews["sentiment_label"] = [item[0] for item in scored]
    reviews["sentiment_score"] = [item[1] for item in scored]
    return customers, orders, reviews


def build_memory_database(customers: pd.DataFrame, orders: pd.DataFrame, reviews: pd.DataFrame) -> sqlite3.Connection:
    conn = sqlite3.connect(":memory:")
    customers.to_sql("customers", conn, if_exists="replace", index=False)
    orders.to_sql("orders", conn, if_exists="replace", index=False)
    reviews.to_sql("reviews", conn, if_exists="replace", index=False)
    return conn


def build_customer_segments(customers: pd.DataFrame, orders: pd.DataFrame, reviews: pd.DataFrame) -> pd.DataFrame:
    customer_metrics = (
        orders.merge(reviews[["order_id", "rating", "sentiment_score"]], on="order_id", how="left")
        .groupby("customer_id")
        .agg(
            total_orders=("order_id", "nunique"),
            lifetime_value=("order_value", "sum"),
            avg_rating=("rating", "mean"),
            avg_sentiment_score=("sentiment_score", "mean"),
            last_order_date=("order_date", "max"),
            return_rate=("is_returned", "mean"),
        )
        .reset_index()
    )
    customer_metrics = customer_metrics.merge(customers, on="customer_id", how="left")
    customer_metrics["lifetime_value"] = customer_metrics["lifetime_value"].round(2)
    customer_metrics["avg_rating"] = customer_metrics["avg_rating"].round(2)
    customer_metrics["avg_sentiment_score"] = customer_metrics["avg_sentiment_score"].round(3)
    customer_metrics["return_rate_pct"] = (customer_metrics["return_rate"] * 100).round(2)

    def assign_segment(row: pd.Series) -> str:
        if row["lifetime_value"] >= 800 and row["avg_sentiment_score"] < -0.15:
            return "High-Value Detractor"
        if row["lifetime_value"] >= 800 and row["avg_sentiment_score"] >= 0.15:
            return "Loyal Promoter"
        if row["total_orders"] == 1 and row["avg_sentiment_score"] < 0:
            return "New At-Risk Customer"
        if row["return_rate_pct"] >= 30:
            return "Return-Risk Customer"
        return "Neutral / Nurture"

    customer_metrics["customer_segment"] = customer_metrics.apply(assign_segment, axis=1)
    return customer_metrics.sort_values("lifetime_value", ascending=False)


def build_product_summary(orders: pd.DataFrame, reviews: pd.DataFrame) -> pd.DataFrame:
    merged = orders.merge(reviews, on=["order_id", "customer_id"], how="left")
    summary = (
        merged.groupby(["product_id", "product_name", "category"])
        .agg(
            revenue=("order_value", "sum"),
            orders=("order_id", "nunique"),
            avg_rating=("rating", "mean"),
            avg_sentiment_score=("sentiment_score", "mean"),
            negative_review_pct=("sentiment_label", lambda x: (x == "negative").mean() * 100),
            return_rate_pct=("is_returned", lambda x: x.mean() * 100),
            top_issue=("review_topic", lambda x: x.value_counts().index[0]),
        )
        .reset_index()
    )
    for column in ["revenue", "avg_rating", "avg_sentiment_score", "negative_review_pct", "return_rate_pct"]:
        summary[column] = summary[column].round(2)
    return summary.sort_values(["revenue", "negative_review_pct"], ascending=[False, False])


def build_ab_test_results(orders: pd.DataFrame) -> pd.DataFrame:
    rows = []
    control = orders[orders["ab_group"] == "control"]
    treatment = orders[orders["ab_group"] == "treatment"]

    for metric in ["converted", "retained_30d"]:
        control_success = int(control[metric].sum())
        treatment_success = int(treatment[metric].sum())
        z_score, p_value = two_proportion_z_test(
            control_success,
            len(control),
            treatment_success,
            len(treatment),
        )
        control_rate = control_success / len(control)
        treatment_rate = treatment_success / len(treatment)
        rows.append(
            {
                "metric": metric,
                "control_rate_pct": round(control_rate * 100, 2),
                "treatment_rate_pct": round(treatment_rate * 100, 2),
                "uplift_pct_points": round((treatment_rate - control_rate) * 100, 2),
                "z_score": z_score,
                "p_value": p_value,
                "significant_at_95": p_value < 0.05,
            }
        )
    return pd.DataFrame(rows)


def generate_executive_summary(
    orders: pd.DataFrame,
    reviews: pd.DataFrame,
    product_summary: pd.DataFrame,
    segments: pd.DataFrame,
    ab_results: pd.DataFrame,
) -> None:
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    total_revenue = orders["order_value"].sum()
    avg_rating = reviews["rating"].mean()
    negative_pct = (reviews["sentiment_label"] == "negative").mean() * 100
    return_rate = orders["is_returned"].mean() * 100
    product_risk_pool = product_summary[product_summary["orders"] >= 2]
    if product_risk_pool.empty:
        product_risk_pool = product_summary
    riskiest_product = product_risk_pool.sort_values(["negative_review_pct", "orders"], ascending=[False, False]).iloc[0]
    top_segment = segments["customer_segment"].value_counts().idxmax()
    conversion_test = ab_results[ab_results["metric"] == "converted"].iloc[0]

    summary = f"""# Executive Summary

## Performance Snapshot

- Total revenue analyzed: ${total_revenue:,.2f}
- Average customer rating: {avg_rating:.2f} out of 5
- Negative review share: {negative_pct:.2f}%
- Return rate: {return_rate:.2f}%
- Largest customer segment: {top_segment}

## Product Risk Insight

The product with the highest negative review rate is **{riskiest_product["product_name"]}**. Its leading issue topic is **{riskiest_product["top_issue"]}**, with a negative review rate of **{riskiest_product["negative_review_pct"]:.2f}%** and return rate of **{riskiest_product["return_rate_pct"]:.2f}%**.

## A/B Test Insight

The treatment group changed conversion by **{conversion_test["uplift_pct_points"]:.2f} percentage points** versus control. The p-value is **{conversion_test["p_value"]:.4f}**, so the result is {"statistically significant at 95% confidence" if conversion_test["significant_at_95"] else "not statistically significant at 95% confidence"}.

## Recommended Actions

1. Prioritize product quality fixes for high-revenue products with above-average negative sentiment.
2. Create a retention campaign for High-Value Detractors and Return-Risk Customers.
3. Monitor delivery, battery, quality, support, and usability topics as operational issue categories.
4. Scale the A/B test only if conversion and retention gains remain significant after additional sample collection.
5. Use the Power BI dashboard to review product sentiment and return risk every week.
"""

    (REPORTS_DIR / "executive_summary.md").write_text(summary, encoding="utf-8")


def main() -> None:
    customers, orders, reviews = load_data()
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)

    segments = build_customer_segments(customers, orders, reviews)
    product_summary = build_product_summary(orders, reviews)
    ab_results = build_ab_test_results(orders)

    segments.to_csv(PROCESSED_DIR / "customer_segments.csv", index=False)
    product_summary.to_csv(PROCESSED_DIR / "product_sentiment_summary.csv", index=False)
    ab_results.to_csv(PROCESSED_DIR / "ab_test_results.csv", index=False)

    with build_memory_database(customers, orders, reviews) as conn:
        segments.to_sql("customer_segments", conn, if_exists="replace", index=False)
        product_summary.to_sql("product_sentiment_summary", conn, if_exists="replace", index=False)
        ab_results.to_sql("ab_test_results", conn, if_exists="replace", index=False)

    generate_executive_summary(orders, reviews, product_summary, segments, ab_results)
    print("Analytics pipeline complete. Outputs saved in data/processed and reports.")


if __name__ == "__main__":
    main()

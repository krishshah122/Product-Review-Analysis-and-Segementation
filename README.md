#Product Review and Analysis

Portfolio project for a data analyst role. It combines real Amazon Reviews 2023 data with simulated business experiment fields to demonstrate product review analytics, sentiment analysis, customer segmentation, SQL reporting, A/B testing, Power BI dashboard planning, and executive summaries.

## Business Problem

An e-commerce company wants to understand what customers are saying in product reviews, which products create customer dissatisfaction, which customer segments are most at risk, and whether a new customer-experience experiment should be scaled.

## Data Sources

Primary review source:

- Amazon Reviews 2023 by McAuley Lab / UCSD
- Default category used by the loader: `All_Beauty`
- Real fields used: review text, review title, rating, user ID, product ID, review timestamp, helpful votes, verified purchase, and product metadata when available

Simulated fields:

- Order value
- Discount percentage
- Return flag
- Customer demographic fields
- Acquisition channel
- A/B test group
- Conversion flag
- 30-day retention flag

These fields are simulated because public review datasets normally do not include private company experiment assignment, conversion, or retention data.

## What This Project Shows

- Real data ingestion from compressed JSONL
- Data cleaning and feature engineering
- SQL analytics with KPI, product, customer, and experiment queries
- Sentiment analysis using review text and ratings
- Customer segmentation using value, review sentiment, and return risk
- Simulated A/B testing with uplift, z-score, p-value, and significance flag
- Power BI dashboard design with suggested DAX measures
- Executive summaries generated from analytical outputs

## Project Structure

```text
.
|-- data/
|   |-- raw/
|   |   |-- customers.csv              # Portfolio-ready customer table
|   |   |-- orders.csv                 # Simulated order and experiment table
|   |   `-- product_reviews.csv        # Real Amazon review sample
|   `-- processed/
|       |-- ab_test_results.csv
|       |-- customer_segments.csv
|       `-- product_sentiment_summary.csv
|-- docs/
|-- reports/
|-- sql/
|-- src/
|   |-- prepare_amazon_reviews_2023.py
|   |-- generate_data.py               # Backup synthetic generator
|   `-- run_analytics.py
`-- requirements.txt
```

## Quick Start With Real Amazon Reviews 2023 Data

```bash
python src/prepare_amazon_reviews_2023.py --category All_Beauty --sample-size 5000
python src/run_analytics.py
```

The first command streams an Amazon Reviews 2023 category file, samples real reviews, and creates the raw CSV tables. The second command runs sentiment analysis, segmentation, A/B test analytics, and the executive report.

If you already downloaded the `.jsonl.gz` files manually, you can use local files:

```bash
python src/prepare_amazon_reviews_2023.py --review-file path/to/All_Beauty.jsonl.gz --meta-file path/to/meta_All_Beauty.jsonl.gz
```

## Backup Synthetic Data Mode

If you cannot download the real dataset because of network or storage limits, use:

```bash
python src/generate_data.py
python src/run_analytics.py
```

## Outputs

- `data/raw/product_reviews.csv`
- `data/raw/customers.csv`
- `data/raw/orders.csv`
- `data/processed/customer_segments.csv`
- `data/processed/product_sentiment_summary.csv`
- `data/processed/ab_test_results.csv`
- `reports/executive_summary.md`

## Dashboard Pages To Build In Power BI

1. Executive Overview: revenue, average rating, review volume, sentiment mix, return rate
2. Product Intelligence: product-level rating, sentiment, issues, return risk
3. Customer Segments: loyal customers, at-risk customers, high-value detractors
4. A/B Test Results: control vs treatment conversion, retention, statistical significance
5. Review Explorer: review text, sentiment, topic, product, verified purchase, helpful votes, and date filters

## Recommended Resume Project Title

**AI-Powered Product Review Intelligence System | Amazon Reviews 2023, SQL, Python, Power BI, Sentiment Analysis, A/B Testing**

## How To Explain It In Interviews

> I built an end-to-end analytics project using real Amazon Reviews 2023 data. I prepared review and product metadata, engineered business-ready order and customer tables, scored sentiment, segmented customers, wrote SQL analytics, simulated an A/B testing framework, and designed a Power BI dashboard with executive recommendations. The A/B test fields are simulated because public review datasets do not include private experiment assignment or conversion tracking.

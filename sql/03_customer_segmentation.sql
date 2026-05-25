-- Customer-level analytical base table
WITH customer_metrics AS (
    SELECT
        c.customer_id,
        c.region,
        c.age_group,
        c.acquisition_channel,
        COUNT(DISTINCT o.order_id) AS total_orders,
        ROUND(SUM(o.order_value), 2) AS lifetime_value,
        ROUND(AVG(r.rating), 2) AS avg_rating,
        ROUND(AVG(r.sentiment_score), 3) AS avg_sentiment_score,
        MAX(o.order_date) AS last_order_date,
        ROUND(AVG(o.is_returned) * 100, 2) AS return_rate_pct
    FROM customers c
    JOIN orders o ON c.customer_id = o.customer_id
    LEFT JOIN reviews r ON o.order_id = r.order_id
    GROUP BY c.customer_id, c.region, c.age_group, c.acquisition_channel
)
SELECT
    *,
    CASE
        WHEN lifetime_value >= 800 AND avg_sentiment_score < -0.15 THEN 'High-Value Detractor'
        WHEN lifetime_value >= 800 AND avg_sentiment_score >= 0.15 THEN 'Loyal Promoter'
        WHEN total_orders = 1 AND avg_sentiment_score < 0 THEN 'New At-Risk Customer'
        WHEN return_rate_pct >= 30 THEN 'Return-Risk Customer'
        ELSE 'Neutral / Nurture'
    END AS customer_segment
FROM customer_metrics
ORDER BY lifetime_value DESC;

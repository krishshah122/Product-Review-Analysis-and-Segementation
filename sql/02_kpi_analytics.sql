-- Monthly business performance
SELECT
    substr(order_date, 1, 7) AS month,
    COUNT(*) AS orders,
    ROUND(SUM(order_value), 2) AS revenue,
    ROUND(AVG(order_value), 2) AS avg_order_value,
    ROUND(AVG(is_returned) * 100, 2) AS return_rate_pct
FROM orders
GROUP BY month
ORDER BY month;

-- Sentiment distribution by product category
SELECT
    o.category,
    r.sentiment_label,
    COUNT(*) AS reviews,
    ROUND(AVG(r.rating), 2) AS avg_rating,
    ROUND(AVG(r.sentiment_score), 3) AS avg_sentiment_score
FROM reviews r
JOIN orders o ON r.order_id = o.order_id
GROUP BY o.category, r.sentiment_label
ORDER BY o.category, reviews DESC;

-- Products with high revenue but weak customer sentiment
SELECT
    o.product_name,
    o.category,
    ROUND(SUM(o.order_value), 2) AS revenue,
    COUNT(r.review_id) AS review_count,
    ROUND(AVG(r.rating), 2) AS avg_rating,
    ROUND(AVG(CASE WHEN r.sentiment_label = 'negative' THEN 1.0 ELSE 0.0 END) * 100, 2) AS negative_review_pct,
    ROUND(AVG(o.is_returned) * 100, 2) AS return_rate_pct
FROM orders o
JOIN reviews r ON o.order_id = r.order_id
GROUP BY o.product_name, o.category
HAVING review_count >= 2
ORDER BY revenue DESC, negative_review_pct DESC;

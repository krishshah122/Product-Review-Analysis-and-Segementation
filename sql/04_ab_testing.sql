-- A/B test performance by experiment group
SELECT
    ab_group,
    COUNT(*) AS users_or_orders,
    ROUND(AVG(converted) * 100, 2) AS conversion_rate_pct,
    ROUND(AVG(retained_30d) * 100, 2) AS retention_rate_pct,
    ROUND(AVG(order_value), 2) AS avg_order_value,
    ROUND(AVG(is_returned) * 100, 2) AS return_rate_pct
FROM orders
GROUP BY ab_group;


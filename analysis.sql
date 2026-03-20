-- =============================================================================
-- retail-bi-pipeline | analysis.sql
-- =============================================================================
-- Business intelligence queries for the Peruvian bodega dataset.
-- Database: output/bodega_analisis.db (SQLite 3)
-- Period  : January 2024 – August 2024
-- Run     : sqlite3 output/bodega_analisis.db < analysis.sql
-- =============================================================================


-- =============================================================================
-- SECTION 1 — REVENUE OVERVIEW
-- =============================================================================

-- 1.1  Top-line KPIs for the full period
SELECT
    COUNT(*)                            AS total_transactions,
    ROUND(SUM(total), 2)               AS total_revenue,
    ROUND(AVG(total), 2)               AS avg_ticket,
    ROUND(MIN(total), 2)               AS min_ticket,
    ROUND(MAX(total), 2)               AS max_ticket,
    COUNT(DISTINCT DATE(timestamp))    AS trading_days
FROM fact_ventas;


-- 1.2  Monthly revenue trend with month-over-month growth
WITH monthly AS (
    SELECT
        mes,
        ROUND(SUM(total), 2)  AS revenue,
        COUNT(*)               AS transactions
    FROM fact_ventas
    GROUP BY mes
)
SELECT
    mes,
    revenue,
    transactions,
    ROUND(
        (revenue - LAG(revenue) OVER (ORDER BY mes)) * 100.0
        / LAG(revenue) OVER (ORDER BY mes),
        1
    )                          AS mom_growth_pct,
    ROUND(SUM(revenue) OVER (ORDER BY mes), 2) AS cumulative_revenue
FROM monthly
ORDER BY mes;


-- 1.3  Weekly revenue with 4-week rolling average
WITH weekly AS (
    SELECT
        semana,
        ROUND(SUM(total), 2) AS revenue
    FROM fact_ventas
    GROUP BY semana
)
SELECT
    semana,
    revenue,
    ROUND(
        AVG(revenue) OVER (
            ORDER BY semana
            ROWS BETWEEN 3 PRECEDING AND CURRENT ROW
        ),
        2
    ) AS rolling_4w_avg
FROM weekly
ORDER BY semana;


-- =============================================================================
-- SECTION 2 — PRODUCT ANALYSIS
-- =============================================================================

-- 2.1  ABC classification by revenue contribution
WITH product_revenue AS (
    SELECT
        p.producto,
        p.categoria,
        ROUND(SUM(v.total), 2)                                        AS revenue,
        ROUND(SUM(v.total) * 100.0 / SUM(SUM(v.total)) OVER (), 2)   AS pct_of_total,
        ROUND(SUM(SUM(v.total)) OVER (
            ORDER BY SUM(v.total) DESC
            ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
        ) * 100.0 / SUM(SUM(v.total)) OVER (), 2)                    AS cumulative_pct
    FROM fact_ventas v
    JOIN dim_productos p USING (producto_id)
    GROUP BY p.producto, p.categoria
)
SELECT
    producto,
    categoria,
    revenue,
    pct_of_total,
    cumulative_pct,
    CASE
        WHEN cumulative_pct <= 80 THEN 'A'
        WHEN cumulative_pct <= 95 THEN 'B'
        ELSE                           'C'
    END AS abc_class
FROM product_revenue
ORDER BY revenue DESC;


-- 2.2  Product performance: revenue, units, frequency, avg ticket
SELECT
    p.producto,
    p.categoria,
    COUNT(*)                        AS num_transactions,
    SUM(v.cantidad)                 AS units_sold,
    ROUND(SUM(v.total), 2)         AS total_revenue,
    ROUND(AVG(v.total), 2)         AS avg_ticket,
    ROUND(AVG(v.cantidad), 2)      AS avg_units_per_txn,
    ROUND(SUM(v.total) * 1.0
          / COUNT(DISTINCT DATE(v.timestamp)), 2) AS revenue_per_trading_day
FROM fact_ventas v
JOIN dim_productos p USING (producto_id)
GROUP BY p.producto, p.categoria
ORDER BY total_revenue DESC;


-- 2.3  Revenue rank within each category (window function)
SELECT
    p.categoria,
    p.producto,
    ROUND(SUM(v.total), 2)  AS revenue,
    RANK() OVER (
        PARTITION BY p.categoria
        ORDER BY SUM(v.total) DESC
    )                        AS rank_in_category
FROM fact_ventas v
JOIN dim_productos p USING (producto_id)
GROUP BY p.categoria, p.producto
ORDER BY p.categoria, rank_in_category;


-- =============================================================================
-- SECTION 3 — CATEGORY ANALYSIS
-- =============================================================================

-- 3.1  Category KPIs with percentage contribution
SELECT
    p.categoria,
    COUNT(*)                                                           AS transactions,
    SUM(v.cantidad)                                                    AS units_sold,
    ROUND(SUM(v.total), 2)                                            AS revenue,
    ROUND(AVG(v.total), 2)                                            AS avg_ticket,
    ROUND(SUM(v.total) * 100.0 / SUM(SUM(v.total)) OVER (), 2)       AS revenue_share_pct,
    COUNT(DISTINCT p.producto)                                         AS distinct_skus
FROM fact_ventas v
JOIN dim_productos p USING (producto_id)
GROUP BY p.categoria
ORDER BY revenue DESC;


-- 3.2  Category revenue per month (pivot-style using CASE)
SELECT
    p.categoria,
    ROUND(SUM(CASE WHEN v.mes = 1 THEN v.total ELSE 0 END), 2) AS jan,
    ROUND(SUM(CASE WHEN v.mes = 2 THEN v.total ELSE 0 END), 2) AS feb,
    ROUND(SUM(CASE WHEN v.mes = 3 THEN v.total ELSE 0 END), 2) AS mar,
    ROUND(SUM(CASE WHEN v.mes = 4 THEN v.total ELSE 0 END), 2) AS apr,
    ROUND(SUM(CASE WHEN v.mes = 5 THEN v.total ELSE 0 END), 2) AS may,
    ROUND(SUM(CASE WHEN v.mes = 6 THEN v.total ELSE 0 END), 2) AS jun,
    ROUND(SUM(CASE WHEN v.mes = 7 THEN v.total ELSE 0 END), 2) AS jul,
    ROUND(SUM(CASE WHEN v.mes = 8 THEN v.total ELSE 0 END), 2) AS aug,
    ROUND(SUM(v.total), 2)                                     AS total
FROM fact_ventas v
JOIN dim_productos p USING (producto_id)
GROUP BY p.categoria
ORDER BY total DESC;


-- =============================================================================
-- SECTION 4 — TIME-BASED ANALYSIS
-- =============================================================================

-- 4.1  Hourly traffic: transactions, revenue and share of day
WITH hourly AS (
    SELECT
        hora,
        COUNT(*)              AS transactions,
        ROUND(SUM(total), 2)  AS revenue
    FROM fact_ventas
    GROUP BY hora
)
SELECT
    hora,
    transactions,
    revenue,
    ROUND(transactions * 100.0 / SUM(transactions) OVER (), 2) AS txn_share_pct,
    CASE
        WHEN hora BETWEEN 7  AND 9  THEN 'morning_peak'
        WHEN hora BETWEEN 20 AND 21 THEN 'evening_peak'
        WHEN hora BETWEEN 10 AND 19 THEN 'mid_day'
        ELSE                             'off_peak'
    END AS time_segment
FROM hourly
ORDER BY hora;


-- 4.2  Day-of-week performance
SELECT
    dia_sem,
    COUNT(*)              AS transactions,
    ROUND(SUM(total), 2)  AS revenue,
    ROUND(AVG(total), 2)  AS avg_ticket,
    ROUND(SUM(total) * 100.0 / SUM(SUM(total)) OVER (), 2) AS revenue_share_pct
FROM fact_ventas
GROUP BY dia_sem
ORDER BY
    CASE dia_sem
        WHEN 'Monday'    THEN 1
        WHEN 'Tuesday'   THEN 2
        WHEN 'Wednesday' THEN 3
        WHEN 'Thursday'  THEN 4
        WHEN 'Friday'    THEN 5
        WHEN 'Saturday'  THEN 6
        WHEN 'Sunday'    THEN 7
    END;


-- 4.3  Best and worst 10 trading days by revenue
(
    SELECT
        DATE(timestamp) AS fecha,
        COUNT(*)         AS transactions,
        ROUND(SUM(total), 2) AS revenue,
        'top_10' AS segment
    FROM fact_ventas
    GROUP BY DATE(timestamp)
    ORDER BY revenue DESC
    LIMIT 10
)
UNION ALL
(
    SELECT
        DATE(timestamp) AS fecha,
        COUNT(*),
        ROUND(SUM(total), 2),
        'bottom_10'
    FROM fact_ventas
    GROUP BY DATE(timestamp)
    ORDER BY revenue ASC
    LIMIT 10
)
ORDER BY segment, revenue DESC;


-- =============================================================================
-- SECTION 5 — SUPPLIER ANALYSIS
-- =============================================================================

-- 5.1  Revenue and SKU count per supplier
SELECT
    s.nombre            AS supplier,
    s.ciudad,
    COUNT(DISTINCT p.producto_id)        AS skus_supplied,
    COUNT(v.venta_id)                    AS transactions,
    ROUND(SUM(v.total), 2)              AS revenue,
    ROUND(SUM(v.total) * 100.0
          / SUM(SUM(v.total)) OVER (), 2) AS revenue_share_pct,
    ROUND(AVG(v.total), 2)              AS avg_ticket
FROM fact_ventas v
JOIN dim_productos p  USING (producto_id)
JOIN dim_proveedores s ON p.proveedor_id = s.proveedor_id
GROUP BY s.nombre, s.ciudad
ORDER BY revenue DESC;


-- =============================================================================
-- SECTION 6 — ADVANCED ANALYTICS
-- =============================================================================

-- 6.1  Revenue per trading day — rolling 7-day average (trend smoothing)
WITH daily AS (
    SELECT
        DATE(timestamp)       AS fecha,
        ROUND(SUM(total), 2)  AS revenue,
        COUNT(*)              AS transactions
    FROM fact_ventas
    GROUP BY DATE(timestamp)
)
SELECT
    fecha,
    revenue,
    transactions,
    ROUND(
        AVG(revenue) OVER (
            ORDER BY fecha
            ROWS BETWEEN 6 PRECEDING AND CURRENT ROW
        ),
        2
    ) AS rolling_7d_avg,
    ROUND(
        revenue - AVG(revenue) OVER (
            ORDER BY fecha
            ROWS BETWEEN 6 PRECEDING AND CURRENT ROW
        ),
        2
    ) AS deviation_from_avg
FROM daily
ORDER BY fecha;


-- 6.2  Product cross-sell candidates:
--      pairs of products bought on the same day (market basket proxy)
WITH daily_products AS (
    SELECT
        DATE(timestamp) AS fecha,
        p.producto
    FROM fact_ventas v
    JOIN dim_productos p USING (producto_id)
),
pairs AS (
    SELECT
        a.producto   AS product_a,
        b.producto   AS product_b,
        COUNT(*)     AS co_occurrence_days
    FROM daily_products a
    JOIN daily_products b
        ON  a.fecha    = b.fecha
        AND a.producto < b.producto
    GROUP BY a.producto, b.producto
)
SELECT
    product_a,
    product_b,
    co_occurrence_days
FROM pairs
WHERE co_occurrence_days >= 10
ORDER BY co_occurrence_days DESC
LIMIT 20;


-- 6.3  Month-over-month revenue by category with growth flag
WITH cat_monthly AS (
    SELECT
        p.categoria,
        v.mes,
        ROUND(SUM(v.total), 2) AS revenue
    FROM fact_ventas v
    JOIN dim_productos p USING (producto_id)
    GROUP BY p.categoria, v.mes
)
SELECT
    categoria,
    mes,
    revenue,
    LAG(revenue) OVER (PARTITION BY categoria ORDER BY mes) AS prev_month,
    ROUND(
        (revenue - LAG(revenue) OVER (PARTITION BY categoria ORDER BY mes))
        * 100.0
        / NULLIF(LAG(revenue) OVER (PARTITION BY categoria ORDER BY mes), 0),
        1
    )                    AS mom_growth_pct,
    CASE
        WHEN revenue > LAG(revenue) OVER (PARTITION BY categoria ORDER BY mes)
            THEN 'growth'
        WHEN revenue < LAG(revenue) OVER (PARTITION BY categoria ORDER BY mes)
            THEN 'decline'
        ELSE 'flat'
    END                  AS trend
FROM cat_monthly
ORDER BY categoria, mes;


-- 6.4  Running revenue milestone tracker (25 %, 50 %, 75 %, 100 % of total)
WITH daily AS (
    SELECT
        DATE(timestamp)                          AS fecha,
        ROUND(SUM(total), 2)                     AS revenue,
        ROUND(SUM(SUM(total)) OVER (
            ORDER BY DATE(timestamp)
        ), 2)                                    AS cumulative_revenue,
        ROUND(SUM(SUM(total)) OVER (), 2)        AS grand_total
    FROM fact_ventas
    GROUP BY DATE(timestamp)
)
SELECT
    fecha,
    revenue,
    cumulative_revenue,
    ROUND(cumulative_revenue * 100.0 / grand_total, 1) AS cumulative_pct
FROM daily
WHERE ROUND(cumulative_revenue * 100.0 / grand_total, 0) IN (25, 50, 75, 100)
   OR fecha = (SELECT MIN(DATE(timestamp)) FROM fact_ventas)
ORDER BY fecha;

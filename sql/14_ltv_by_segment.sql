-- LTV esperado por segmento RFM. Leia como alerta, não como meta.
--
-- Campeões e leais são definidos por ainda pagarem e pagarem muito.
-- O churn observado dentro desses recortes fica perto de zero e a
-- fórmula ARPU / churn dispara ou fica nula. Isso não é um cliente
-- que vale infinito: é a fórmula usada no lugar errado.
--
-- O número que se compara entre segmentos sem essa armadilha é o
-- LTV histórico (também censurado à direita para os recentes).
-- A regra de segmento é a mesma de sql/06_rfm_segmentation.sql.

WITH paid AS (
    SELECT
        company_id,
        MAX(paid_at) AS last_paid_at,
        COUNT(*) AS frequency,
        SUM(amount_brl) AS monetary
    FROM invoices
    WHERE status = 'paid' AND invoice_type = 'subscription'
    GROUP BY company_id
),

scored AS (
    SELECT
        p.company_id,
        p.monetary,
        NTILE(5) OVER (
            ORDER BY date_diff('day', p.last_paid_at, (SELECT as_of_date FROM params)) DESC
        ) AS r_score,
        NTILE(5) OVER (ORDER BY p.frequency ASC) AS f_score,
        NTILE(5) OVER (ORDER BY p.monetary ASC) AS m_score
    FROM paid AS p
),

rfm AS (
    SELECT
        company_id,
        monetary,
        CASE
            WHEN r_score >= 4 AND f_score >= 4 AND m_score >= 4 THEN 'champion'
            WHEN r_score <= 2 AND f_score >= 3 AND m_score >= 3 THEN 'at_risk'
            WHEN r_score >= 4 AND f_score <= 2 THEN 'recent'
            WHEN f_score >= 4 AND m_score >= 3 THEN 'loyal'
            WHEN r_score <= 2 AND f_score <= 2 THEN 'hibernating'
            WHEN r_score >= 3 AND f_score >= 3 THEN 'promising'
            ELSE 'regular'
        END AS segment_code
    FROM scored
),

life AS (
    SELECT
        company_id,
        COUNT(CASE WHEN ending_mrr > 0 THEN 1 END) AS active_months
    FROM mrr_movements
    GROUP BY company_id
)

SELECT
    r.segment_code,
    CASE r.segment_code
        WHEN 'champion' THEN 'Campeões'
        WHEN 'loyal' THEN 'Leais'
        WHEN 'promising' THEN 'Promissores'
        WHEN 'recent' THEN 'Recentes'
        WHEN 'at_risk' THEN 'Em risco'
        WHEN 'hibernating' THEN 'Hibernando'
        ELSE 'Regulares'
    END AS segment_name,
    COUNT(*) AS customers,
    AVG(r.monetary) AS avg_historical_ltv,
    SUM(r.monetary) / NULLIF(SUM(l.active_months), 0) AS arpu,
    SUM(CASE WHEN ch.company_id IS NOT NULL THEN 1 ELSE 0 END) * 1.0
        / NULLIF(SUM(l.active_months), 0) AS monthly_churn_rate,
    (
        (SUM(r.monetary) / NULLIF(SUM(l.active_months), 0))
        * (SELECT gross_margin FROM params)
    ) / NULLIF(
        SUM(CASE WHEN ch.company_id IS NOT NULL THEN 1 ELSE 0 END) * 1.0
            / NULLIF(SUM(l.active_months), 0),
        0
    ) AS expected_ltv
FROM rfm AS r
INNER JOIN life AS l ON l.company_id = r.company_id
LEFT JOIN churn_events AS ch ON ch.company_id = r.company_id
GROUP BY r.segment_code
ORDER BY avg_historical_ltv DESC;

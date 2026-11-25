-- Pergunta: qual o LTV por porte da PME?
--
-- Porte é um atributo da empresa, não um recorte de sobrevivência.
-- Por isso o churn mensal aqui não explode nem zera por construção,
-- ao contrário do LTV esperado por segmento RFM (veja sql/14_ltv_by_segment.sql).
--
-- LTV histórico = soma das faturas de assinatura pagas.
-- Está censurado à direita: quem entrou há pouco ainda não acumulou a vida toda.
--
-- Churn mensal = cancelamentos / meses ativos.
-- LTV esperado = (ARPU × margem) / churn mensal.
-- ARPU = receita paga de assinatura / meses ativos.
--
-- Premissas: churn constante, sem expansão futura, margem única em
-- params.gross_margin. É um modelo de guardanapo, útil para comparar
-- portes, não para precificar um contrato.

WITH monetary AS (
    SELECT company_id, SUM(amount_brl) AS monetary
    FROM invoices
    WHERE status = 'paid' AND invoice_type = 'subscription'
    GROUP BY company_id
),

life AS (
    SELECT
        company_id,
        COUNT(CASE WHEN ending_mrr > 0 THEN 1 END) AS active_months
    FROM mrr_movements
    GROUP BY company_id
),

exposure AS (
    SELECT
        c.porte,
        COUNT(*) AS customers,
        SUM(COALESCE(mo.monetary, 0)) AS historical_revenue,
        AVG(COALESCE(mo.monetary, 0)) AS avg_historical_ltv,
        SUM(l.active_months) AS active_months,
        SUM(CASE WHEN ch.company_id IS NOT NULL THEN 1 ELSE 0 END) AS churned_customers,
        AVG(CASE WHEN s.status = 'active' THEN s.current_mrr_brl END) AS avg_active_mrr
    FROM subscriptions AS s
    INNER JOIN companies AS c ON c.company_id = s.company_id
    INNER JOIN life AS l ON l.company_id = s.company_id
    LEFT JOIN monetary AS mo ON mo.company_id = s.company_id
    LEFT JOIN churn_events AS ch ON ch.company_id = s.company_id
    GROUP BY c.porte
)

SELECT
    e.porte,
    CASE e.porte
        WHEN 'mei' THEN 'MEI'
        WHEN 'micro' THEN 'Microempresa'
        WHEN 'pequena' THEN 'Pequena'
        WHEN 'media' THEN 'Média'
        ELSE e.porte
    END AS porte_name,
    e.customers,
    e.avg_historical_ltv,
    e.avg_active_mrr,
    e.active_months,
    e.churned_customers,
    e.historical_revenue / NULLIF(e.active_months, 0) AS arpu,
    e.churned_customers * 1.0 / NULLIF(e.active_months, 0) AS monthly_churn_rate,
    (
        (e.historical_revenue / NULLIF(e.active_months, 0)) * p.gross_margin
    ) / NULLIF(e.churned_customers * 1.0 / NULLIF(e.active_months, 0), 0) AS expected_ltv
FROM exposure AS e
CROSS JOIN params AS p
ORDER BY e.avg_active_mrr;

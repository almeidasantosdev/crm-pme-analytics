-- Pergunta: uma coorte de clientes ainda está ativa (e pagando quanto)
-- depois de N meses?
--
-- Coorte = mês do primeiro MRR (movimento new_mrr > 0).
-- Idade 0 é o mês de entrada. Retenção de logos na idade 0 é 1.
-- Retenção de receita pode passar de 1 nas idades seguintes por causa
-- da expansão. Isso é desejável: a métrica inclui upsell.
--
-- Meses sem nenhum cliente ativo entram com zero. Sem essa grade,
-- o heatmap esconderia a idade em que a coorte zerou.
--
-- Grão: coorte × idade × porte × canal de aquisição.

WITH firsts AS (
    SELECT
        m.company_id,
        m.month_start AS cohort_month,
        m.new_mrr AS initial_mrr,
        c.porte,
        s.channel
    FROM mrr_movements AS m
    INNER JOIN companies AS c ON c.company_id = m.company_id
    INNER JOIN subscriptions AS s ON s.company_id = m.company_id
    WHERE m.new_mrr > 0
),

bounds AS (
    SELECT
        cohort_month,
        porte,
        channel,
        COUNT(*) AS cohort_customers,
        SUM(initial_mrr) AS cohort_initial_mrr,
        date_diff(
            'month',
            cohort_month,
            (SELECT MAX(month_start) FROM mrr_movements)
        ) AS max_age
    FROM firsts
    GROUP BY cohort_month, porte, channel
),

ages AS (
    SELECT
        b.cohort_month,
        b.porte,
        b.channel,
        b.cohort_customers,
        b.cohort_initial_mrr,
        u.age_months
    FROM bounds AS b,
        LATERAL generate_series(0, b.max_age) AS u(age_months)
),

retained AS (
    SELECT
        f.cohort_month,
        f.porte,
        f.channel,
        date_diff('month', f.cohort_month, a.month_start) AS age_months,
        COUNT(*) AS active_customers,
        SUM(a.ending_mrr) AS retained_mrr
    FROM firsts AS f
    INNER JOIN mrr_movements AS a
        ON a.company_id = f.company_id
        AND a.ending_mrr > 0
    GROUP BY f.cohort_month, f.porte, f.channel, date_diff('month', f.cohort_month, a.month_start)
)

SELECT
    g.cohort_month,
    g.age_months,
    g.porte,
    g.channel,
    g.cohort_customers,
    COALESCE(r.active_customers, 0) AS active_customers,
    COALESCE(r.active_customers, 0) * 1.0 / g.cohort_customers AS logo_retention,
    g.cohort_initial_mrr,
    COALESCE(r.retained_mrr, 0) AS retained_mrr,
    COALESCE(r.retained_mrr, 0) / NULLIF(g.cohort_initial_mrr, 0) AS revenue_retention
FROM ages AS g
LEFT JOIN retained AS r
    ON r.cohort_month = g.cohort_month
    AND r.porte = g.porte
    AND r.channel = g.channel
    AND r.age_months = g.age_months
ORDER BY g.cohort_month, g.age_months, g.porte, g.channel;

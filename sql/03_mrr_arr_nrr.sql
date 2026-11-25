-- Pergunta: como evoluem MRR, ARR de run-rate e a retenção de receita?
--
-- Identidade de cada cliente-mês, e portanto de qualquer soma:
--   ending = beginning + new + expansion - contraction - churn
--
-- NRR (net revenue retention) não inclui cliente novo:
--   (beginning + expansion - contraction - churn) / beginning
--   = (ending - new) / beginning
--
-- GRR (gross revenue retention) também ignora expansão, então não passa de 1
-- quando a identidade está correta:
--   (beginning - contraction - churn) / beginning
--
-- Quick ratio = (new + expansion) / (contraction + churn).
-- ARR de run-rate = MRR final × 12. Não é receita contratada anual.
--
-- Grão: mês × porte × canal de aquisição × plano.
-- Some os componentes e recalcule as taxas. Não faça média de NRR.

SELECT
    m.month_start,
    c.porte,
    s.channel,
    s.plan,
    SUM(m.beginning_mrr) AS beginning_mrr,
    SUM(m.new_mrr) AS new_mrr,
    SUM(m.expansion_mrr) AS expansion_mrr,
    SUM(m.contraction_mrr) AS contraction_mrr,
    SUM(m.churn_mrr) AS churn_mrr,
    SUM(m.ending_mrr) AS ending_mrr,
    SUM(m.ending_mrr) * 12 AS ending_arr,
    COUNT(CASE WHEN m.beginning_mrr > 0 THEN 1 END) AS beginning_customers,
    COUNT(CASE WHEN m.new_mrr > 0 THEN 1 END) AS new_customers,
    COUNT(CASE WHEN m.churn_mrr > 0 THEN 1 END) AS churned_customers,
    COUNT(CASE WHEN m.ending_mrr > 0 THEN 1 END) AS ending_customers,
    (
        SUM(m.beginning_mrr) + SUM(m.expansion_mrr) - SUM(m.contraction_mrr) - SUM(m.churn_mrr)
    ) / NULLIF(SUM(m.beginning_mrr), 0) AS nrr,
    (
        SUM(m.beginning_mrr) - SUM(m.contraction_mrr) - SUM(m.churn_mrr)
    ) / NULLIF(SUM(m.beginning_mrr), 0) AS grr,
    (SUM(m.new_mrr) + SUM(m.expansion_mrr))
        / NULLIF(SUM(m.contraction_mrr) + SUM(m.churn_mrr), 0) AS quick_ratio
FROM mrr_movements AS m
INNER JOIN subscriptions AS s ON s.company_id = m.company_id
INNER JOIN companies AS c ON c.company_id = m.company_id
GROUP BY m.month_start, c.porte, s.channel, s.plan
ORDER BY m.month_start, c.porte, s.channel, s.plan;

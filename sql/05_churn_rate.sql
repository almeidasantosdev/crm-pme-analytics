-- Pergunta: qual a taxa mensal de cancelamento de logos e de receita?
--
-- Denominador = base no início do mês (beginning_mrr > 0).
-- Cliente novo daquele mês não entra no denominador e não pode cancelar
-- no próprio mês de entrada, por regra do gerador.
--
-- Logo churn  = clientes com churn_mrr > 0 / clientes no início
-- Revenue churn = churn_mrr / beginning_mrr
--
-- Contração não é churn: o cliente continua ativo, pagando menos.

WITH month AS (
    SELECT
        month_start,
        SUM(beginning_mrr) AS beginning_mrr,
        SUM(churn_mrr) AS churn_mrr,
        COUNT(CASE WHEN beginning_mrr > 0 THEN 1 END) AS beginning_customers,
        COUNT(CASE WHEN churn_mrr > 0 THEN 1 END) AS churned_customers
    FROM mrr_movements
    GROUP BY month_start
)

SELECT
    month_start,
    beginning_customers,
    churned_customers,
    churned_customers * 1.0 / NULLIF(beginning_customers, 0) AS logo_churn_rate,
    beginning_mrr,
    churn_mrr,
    churn_mrr / NULLIF(beginning_mrr, 0) AS revenue_churn_rate
FROM month
WHERE beginning_customers > 0
ORDER BY month_start;

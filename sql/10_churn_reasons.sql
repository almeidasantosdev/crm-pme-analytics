-- Pergunta: por que o MRR saiu da base?
--
-- Um evento por assinatura cancelada. mrr_lost é o MRR do último mês
-- ativo, não a soma histórica do cliente.

SELECT
    reason,
    CASE reason
        WHEN 'preco' THEN 'Preço'
        WHEN 'produto' THEN 'Produto'
        WHEN 'suporte' THEN 'Suporte'
        WHEN 'concorrente' THEN 'Concorrente'
        WHEN 'encerrou_atividade' THEN 'Encerrou a atividade'
        WHEN 'baixo_uso' THEN 'Baixo uso'
        ELSE reason
    END AS reason_name,
    COUNT(*) AS customers,
    SUM(mrr_lost) AS mrr_lost,
    AVG(tenure_months) AS avg_tenure_months
FROM churn_events
GROUP BY reason
ORDER BY mrr_lost DESC;

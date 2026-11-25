-- Pergunta: quanto de ACV a carteira aberta deve fechar, ponderado pela etapa?
--
-- Só oportunidades com status = 'open'.
-- A probabilidade é a gravada na oportunidade (função da etapa atual),
-- não um segundo mapa escondido na consulta.
--
-- Pipeline nominal = soma de ACV.
-- Pipeline ponderado = soma de ACV × probabilidade.
-- weighted_mrr é a mesma conta em MRR, para quem planeja receita recorrente
-- e não contrato anual.
--
-- ACV = MRR × 12 + taxa de setup. Setup não entra no MRR.
-- A data esperada pode passar da data de corte: é previsão, não fato.

SELECT
    CAST(date_trunc('month', o.expected_close_date) AS DATE) AS close_month,
    o.stage,
    o.channel,
    c.porte,
    COUNT(*) AS deals,
    SUM(o.acv_brl) AS pipeline_acv,
    SUM(o.acv_brl * o.probability) AS weighted_acv,
    SUM(o.mrr_brl * o.probability) AS weighted_mrr
FROM opportunities AS o
INNER JOIN companies AS c ON c.company_id = o.company_id
WHERE o.status = 'open'
GROUP BY
    CAST(date_trunc('month', o.expected_close_date) AS DATE),
    o.stage,
    o.channel,
    c.porte
ORDER BY 1, 2, 3, 4;

-- Pergunta: quanto custa, em mídia, cada cliente novo de cada canal?
--
-- CAC de campanha = investimento do canal / clientes novos do canal.
-- Atribuição: first-touch. Há um lead por empresa, então não existe
-- multi-touch para repartir.
--
-- Investimento zero (orgânico e indicação) produz CAC nulo de propósito.
-- Isso não quer dizer que o canal seja de graça: salário, ferramenta e
-- tempo comercial ficam de fora. Não é um CAC fully loaded.
--
-- Payback em meses = CAC / MRR médio inicial.
-- payback_months_on_margin usa a margem bruta de params (premissa 80%).

WITH spend AS (
    SELECT channel, SUM(spend_brl) AS spend_brl
    FROM campaigns
    GROUP BY channel
),

wins AS (
    SELECT
        channel,
        COUNT(*) AS new_customers,
        SUM(initial_mrr_brl) AS new_mrr
    FROM subscriptions
    GROUP BY channel
),

joined AS (
    SELECT
        COALESCE(s.channel, w.channel) AS channel,
        COALESCE(s.spend_brl, 0) AS spend_brl,
        COALESCE(w.new_customers, 0) AS new_customers,
        COALESCE(w.new_mrr, 0) AS new_mrr
    FROM spend AS s
    FULL OUTER JOIN wins AS w ON w.channel = s.channel
)

SELECT
    j.channel,
    j.spend_brl,
    j.new_customers,
    j.new_mrr,
    j.new_mrr / NULLIF(j.new_customers, 0) AS avg_initial_mrr,
    CASE
        WHEN j.spend_brl > 0 THEN j.spend_brl / NULLIF(j.new_customers, 0)
    END AS cac_brl,
    CASE
        WHEN j.spend_brl > 0 AND j.new_mrr > 0
            THEN (j.spend_brl / j.new_customers) / (j.new_mrr / j.new_customers)
    END AS payback_months,
    CASE
        WHEN j.spend_brl > 0 AND j.new_mrr > 0
            THEN (j.spend_brl / j.new_customers)
                / ((j.new_mrr / j.new_customers) * p.gross_margin)
    END AS payback_months_on_margin
FROM joined AS j
CROSS JOIN params AS p
ORDER BY j.channel;

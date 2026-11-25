-- Pergunta: quais clientes concentram receita recente e quais esfriaram?
--
-- Recência: dias entre o último pagamento de assinatura e a data de corte.
-- Frequência: quantidade de faturas de assinatura pagas.
-- Valor: soma dessas faturas.
--
-- NTILE(5) com o melhor quintil = 5.
-- Recência ordena do maior intervalo para o menor, então quem pagou
-- há pouco recebe 5. Frequência e valor ordenam do menor para o maior.
--
-- A ordem do CASE importa. Campeão também seria "leal"; a primeira
-- regra que casa é a que vale.
--
-- Fatura de setup fica de fora: RFM aqui descreve a relação recorrente.

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
        p.last_paid_at,
        p.frequency,
        p.monetary,
        date_diff('day', p.last_paid_at, (SELECT as_of_date FROM params)) AS recency_days,
        NTILE(5) OVER (
            ORDER BY date_diff('day', p.last_paid_at, (SELECT as_of_date FROM params)) DESC
        ) AS r_score,
        NTILE(5) OVER (ORDER BY p.frequency ASC) AS f_score,
        NTILE(5) OVER (ORDER BY p.monetary ASC) AS m_score
    FROM paid AS p
),

labeled AS (
    SELECT
        s.*,
        CASE
            WHEN s.r_score >= 4 AND s.f_score >= 4 AND s.m_score >= 4 THEN 'champion'
            WHEN s.r_score <= 2 AND s.f_score >= 3 AND s.m_score >= 3 THEN 'at_risk'
            WHEN s.r_score >= 4 AND s.f_score <= 2 THEN 'recent'
            WHEN s.f_score >= 4 AND s.m_score >= 3 THEN 'loyal'
            WHEN s.r_score <= 2 AND s.f_score <= 2 THEN 'hibernating'
            WHEN s.r_score >= 3 AND s.f_score >= 3 THEN 'promising'
            ELSE 'regular'
        END AS segment_code
    FROM scored AS s
)

SELECT
    l.company_id,
    c.company_name,
    c.porte,
    c.sector,
    c.state_uf,
    sub.channel,
    sub.plan,
    sub.status AS subscription_status,
    l.last_paid_at,
    l.recency_days,
    l.frequency,
    l.monetary,
    l.r_score,
    l.f_score,
    l.m_score,
    l.segment_code,
    CASE l.segment_code
        WHEN 'champion' THEN 'Campeões'
        WHEN 'loyal' THEN 'Leais'
        WHEN 'promising' THEN 'Promissores'
        WHEN 'recent' THEN 'Recentes'
        WHEN 'at_risk' THEN 'Em risco'
        WHEN 'hibernating' THEN 'Hibernando'
        ELSE 'Regulares'
    END AS segment_name
FROM labeled AS l
INNER JOIN companies AS c ON c.company_id = l.company_id
INNER JOIN subscriptions AS sub ON sub.company_id = l.company_id
ORDER BY l.monetary DESC;

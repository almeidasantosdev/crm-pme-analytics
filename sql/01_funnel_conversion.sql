-- Pergunta: onde o funil de aquisição perde volume, por mês, canal e porte?
--
-- Etapas, sempre aninhadas nesta base:
--   lead          uma linha em leads
--   mql           mql_at preenchido
--   sql           sql_at preenchido
--   opportunity   existe oportunidade para o lead
--   won           oportunidade com status = 'won'
--
-- Grão: mês de criação do lead × canal × porte.
-- Para um recorte, some os volumes e só então calcule a taxa.
-- Média de taxas mensais não é a conversão do período.

WITH base AS (
    SELECT
        CAST(date_trunc('month', l.created_at) AS DATE) AS month_start,
        l.channel,
        c.porte,
        l.mql_at,
        l.sql_at,
        o.opportunity_id,
        o.status AS opp_status
    FROM leads AS l
    INNER JOIN companies AS c ON c.company_id = l.company_id
    LEFT JOIN opportunities AS o ON o.lead_id = l.lead_id
)

SELECT
    month_start,
    channel,
    porte,
    COUNT(*) AS leads,
    COUNT(mql_at) AS mqls,
    COUNT(sql_at) AS sqls,
    COUNT(opportunity_id) AS opportunities,
    COUNT(CASE WHEN opp_status = 'won' THEN 1 END) AS wins,
    COUNT(mql_at) * 1.0 / NULLIF(COUNT(*), 0) AS lead_to_mql,
    COUNT(sql_at) * 1.0 / NULLIF(COUNT(mql_at), 0) AS mql_to_sql,
    COUNT(opportunity_id) * 1.0 / NULLIF(COUNT(sql_at), 0) AS sql_to_opportunity,
    COUNT(CASE WHEN opp_status = 'won' THEN 1 END) * 1.0
        / NULLIF(COUNT(opportunity_id), 0) AS opportunity_to_win,
    COUNT(CASE WHEN opp_status = 'won' THEN 1 END) * 1.0 / NULLIF(COUNT(*), 0) AS lead_to_win
FROM base
GROUP BY month_start, channel, porte
ORDER BY month_start, channel, porte;

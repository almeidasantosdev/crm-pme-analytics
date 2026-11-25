-- Pergunta: das oportunidades abertas, quantas chegaram a cada etapa?
--
-- Usa o histórico (opportunity_stages), não opportunities.stage.
-- A etapa gravada na oportunidade é a atual ou a final. Um ganho está
-- em 'ganho'; se o funil contasse só isso, proposta e negociação
-- pareceriam vazias.
--
-- A passagem é obrigatória: não se pula etapa. Por isso, no total,
-- qualificação >= proposta >= negociação >= ganho.

SELECT
    o.channel,
    c.porte,
    s.stage,
    MIN(s.stage_order) AS stage_order,
    COUNT(DISTINCT s.opportunity_id) AS opportunities_reached
FROM opportunity_stages AS s
INNER JOIN opportunities AS o ON o.opportunity_id = s.opportunity_id
INNER JOIN companies AS c ON c.company_id = o.company_id
GROUP BY o.channel, c.porte, s.stage
ORDER BY o.channel, c.porte, stage_order;

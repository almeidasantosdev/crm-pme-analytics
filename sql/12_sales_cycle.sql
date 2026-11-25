-- Pergunta: quantos dias a venda leva, do abrir da oportunidade ao ganho?
--
-- Só ganhos. Perdidos e abertos têm outro relógio e misturá-los
-- encurta ou estica o ciclo sem querer.
-- Mediana ao lado da média porque um negócio longo puxa a média.

SELECT
    channel,
    COUNT(*) AS wins,
    AVG(date_diff('day', created_at, closed_at)) AS avg_cycle_days,
    MEDIAN(date_diff('day', created_at, closed_at)) AS median_cycle_days
FROM opportunities
WHERE status = 'won'
GROUP BY channel
ORDER BY median_cycle_days;

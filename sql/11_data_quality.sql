-- Checagens de integridade da base gerada.
-- violations = 0 em todas as linhas. O teste de integração falha se não for.

SELECT 'duplicate_company' AS check_name, COUNT(*) - COUNT(DISTINCT company_id) AS violations
FROM companies
UNION ALL
SELECT 'duplicate_lead', COUNT(*) - COUNT(DISTINCT lead_id) FROM leads
UNION ALL
SELECT 'duplicate_opportunity', COUNT(*) - COUNT(DISTINCT opportunity_id) FROM opportunities
UNION ALL
SELECT 'duplicate_subscription', COUNT(*) - COUNT(DISTINCT subscription_id) FROM subscriptions
UNION ALL
SELECT 'duplicate_invoice', COUNT(*) - COUNT(DISTINCT invoice_id) FROM invoices
UNION ALL
SELECT 'lead_without_company', COUNT(*)
FROM leads AS l
LEFT JOIN companies AS c ON c.company_id = l.company_id
WHERE c.company_id IS NULL
UNION ALL
SELECT 'contact_without_company', COUNT(*)
FROM contacts AS p
LEFT JOIN companies AS c ON c.company_id = p.company_id
WHERE c.company_id IS NULL
UNION ALL
SELECT 'opportunity_without_lead', COUNT(*)
FROM opportunities AS o
LEFT JOIN leads AS l ON l.lead_id = o.lead_id
WHERE l.lead_id IS NULL
UNION ALL
SELECT 'two_opportunities_per_lead', COUNT(*) FROM (
    SELECT lead_id FROM opportunities GROUP BY lead_id HAVING COUNT(*) > 1
)
UNION ALL
SELECT 'won_without_subscription', COUNT(*)
FROM opportunities AS o
LEFT JOIN subscriptions AS s ON s.opportunity_id = o.opportunity_id
WHERE o.status = 'won' AND s.subscription_id IS NULL
UNION ALL
SELECT 'subscription_without_won', COUNT(*)
FROM subscriptions AS s
LEFT JOIN opportunities AS o ON o.opportunity_id = s.opportunity_id
WHERE o.status IS DISTINCT FROM 'won'
UNION ALL
SELECT 'two_subscriptions_per_company', COUNT(*) FROM (
    SELECT company_id FROM subscriptions GROUP BY company_id HAVING COUNT(*) > 1
)
UNION ALL
SELECT 'sql_without_mql', COUNT(*) FROM leads WHERE sql_at IS NOT NULL AND mql_at IS NULL
UNION ALL
SELECT 'opportunity_without_sql', COUNT(*)
FROM opportunities AS o
INNER JOIN leads AS l ON l.lead_id = o.lead_id
WHERE l.sql_at IS NULL
UNION ALL
SELECT 'negative_mrr_component', COUNT(*)
FROM mrr_movements
WHERE beginning_mrr < 0 OR new_mrr < 0 OR expansion_mrr < 0
    OR contraction_mrr < 0 OR churn_mrr < 0 OR ending_mrr < 0
UNION ALL
SELECT 'mrr_identity_break', COUNT(*)
FROM mrr_movements
WHERE ABS(
    ending_mrr - (beginning_mrr + new_mrr + expansion_mrr - contraction_mrr - churn_mrr)
) > 0.02
UNION ALL
SELECT 'churn_mrr_without_event', COUNT(*)
FROM mrr_movements AS m
LEFT JOIN churn_events AS h ON h.company_id = m.company_id AND h.churn_date = m.month_start
WHERE m.churn_mrr > 0 AND h.churn_id IS NULL
UNION ALL
SELECT 'active_with_end_date', COUNT(*)
FROM subscriptions
WHERE status = 'active' AND end_date IS NOT NULL
UNION ALL
SELECT 'churned_without_end_date', COUNT(*)
FROM subscriptions
WHERE status = 'churned' AND end_date IS NULL
UNION ALL
SELECT 'lead_after_cutoff', COUNT(*)
FROM leads
WHERE created_at > (SELECT as_of_date FROM params)
    OR mql_at > (SELECT as_of_date FROM params)
    OR sql_at > (SELECT as_of_date FROM params)
UNION ALL
SELECT 'close_after_cutoff', COUNT(*)
FROM opportunities
WHERE closed_at > (SELECT as_of_date FROM params)
UNION ALL
SELECT 'open_with_close_date', COUNT(*)
FROM opportunities
WHERE status = 'open' AND closed_at IS NOT NULL
UNION ALL
SELECT 'won_stage_not_ganho', COUNT(*)
FROM opportunities
WHERE status = 'won' AND stage <> 'ganho'
UNION ALL
SELECT 'ticket_without_company', COUNT(*)
FROM support_tickets AS t
LEFT JOIN companies AS c ON c.company_id = t.company_id
WHERE c.company_id IS NULL
UNION ALL
SELECT 'invoice_without_subscription', COUNT(*)
FROM invoices AS i
LEFT JOIN subscriptions AS s ON s.subscription_id = i.subscription_id
WHERE s.subscription_id IS NULL
ORDER BY check_name;

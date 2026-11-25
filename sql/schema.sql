-- Modelo operacional da base fictícia da Nexora (DuckDB).
-- Não há chave estrangeira declarada: a integridade é checada em
-- sql/11_data_quality.sql e na suíte de testes. Em Postgres o mesmo
-- desenho recebe PRIMARY KEY e FOREIGN KEY.
--
-- Grão:
--   companies            uma PME prospect ou cliente
--   contacts             pessoas da PME
--   campaigns            investimento de um canal em um mês
--   leads                um lead por empresa (first-touch)
--   opportunities        no máximo uma oportunidade por lead
--   opportunity_stages   histórico de etapas, não a etapa corrente
--   subscriptions        contrato recorrente dos ganhos
--   mrr_movements        ponte mensal de MRR por cliente
--   invoices             faturas de assinatura e de setup
--   churn_events         cancelamentos
--   support_tickets      atendimentos
--   params               data de corte, margem e semente

CREATE TABLE params (
    as_of_date DATE,
    period_start DATE,
    period_end DATE,
    gross_margin DOUBLE,
    seed INTEGER,
    currency VARCHAR,
    vendor_name VARCHAR,
    product_name VARCHAR
);

CREATE TABLE companies (
    company_id VARCHAR,
    company_name VARCHAR,
    porte VARCHAR,
    sector VARCHAR,
    state_uf VARCHAR,
    city VARCHAR,
    employees INTEGER,
    annual_revenue_brl DOUBLE,
    created_at DATE
);

CREATE TABLE contacts (
    contact_id VARCHAR,
    company_id VARCHAR,
    full_name VARCHAR,
    role VARCHAR,
    email VARCHAR,
    phone VARCHAR,
    is_primary BOOLEAN
);

CREATE TABLE campaigns (
    campaign_id VARCHAR,
    campaign_name VARCHAR,
    channel VARCHAR,
    month_start DATE,
    spend_brl DOUBLE
);

CREATE TABLE leads (
    lead_id VARCHAR,
    company_id VARCHAR,
    contact_id VARCHAR,
    campaign_id VARCHAR,
    channel VARCHAR,
    created_at DATE,
    mql_at DATE,
    sql_at DATE,
    status VARCHAR,
    disqualified_reason VARCHAR
);

CREATE TABLE opportunities (
    opportunity_id VARCHAR,
    lead_id VARCHAR,
    company_id VARCHAR,
    campaign_id VARCHAR,
    channel VARCHAR,
    owner_name VARCHAR,
    plan VARCHAR,
    stage VARCHAR,
    status VARCHAR,
    created_at DATE,
    expected_close_date DATE,
    closed_at DATE,
    mrr_brl DOUBLE,
    setup_fee_brl DOUBLE,
    acv_brl DOUBLE,
    probability DOUBLE,
    loss_reason VARCHAR
);

CREATE TABLE opportunity_stages (
    opportunity_id VARCHAR,
    stage VARCHAR,
    stage_order INTEGER,
    entered_at DATE,
    exited_at DATE
);

CREATE TABLE subscriptions (
    subscription_id VARCHAR,
    company_id VARCHAR,
    opportunity_id VARCHAR,
    plan VARCHAR,
    channel VARCHAR,
    start_date DATE,
    end_date DATE,
    initial_mrr_brl DOUBLE,
    current_mrr_brl DOUBLE,
    status VARCHAR
);

CREATE TABLE mrr_movements (
    company_id VARCHAR,
    month_start DATE,
    beginning_mrr DOUBLE,
    new_mrr DOUBLE,
    expansion_mrr DOUBLE,
    contraction_mrr DOUBLE,
    churn_mrr DOUBLE,
    ending_mrr DOUBLE
);

CREATE TABLE invoices (
    invoice_id VARCHAR,
    company_id VARCHAR,
    subscription_id VARCHAR,
    month_start DATE,
    invoice_type VARCHAR,
    amount_brl DOUBLE,
    status VARCHAR,
    issued_at DATE,
    due_at DATE,
    paid_at DATE
);

CREATE TABLE churn_events (
    churn_id VARCHAR,
    company_id VARCHAR,
    subscription_id VARCHAR,
    churn_date DATE,
    reason VARCHAR,
    mrr_lost DOUBLE,
    tenure_months INTEGER
);

CREATE TABLE support_tickets (
    ticket_id VARCHAR,
    company_id VARCHAR,
    opened_at DATE,
    closed_at DATE,
    priority VARCHAR,
    category VARCHAR,
    status VARCHAR,
    csat INTEGER,
    resolution_hours DOUBLE
);

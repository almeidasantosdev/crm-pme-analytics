# Dicionário da base fictícia

Tudo é produzido por `data/generate.py` (semente 42). Códigos em inglês, rótulos em português nas dimensões.

Data de corte: **31/10/2026**. Moeda: BRL. Margem bruta usada só em payback e LTV: **80%**, gravada em `params.gross_margin`.

## Porte

Faixa de faturamento anual usada só para desenhar a empresa. Não é um enquadramento fiscal consultado.

| Código | Rótulo | Faturamento anual fictício | Pessoas |
| --- | --- | --- | --- |
| `mei` | MEI | 28 a 81 mil | 1 |
| `micro` | Microempresa | 81 a 360 mil | 2 a 9 |
| `pequena` | Pequena | 360 mil a 4,8 milhões | 10 a 49 |
| `media` | Média | 4,8 a 28 milhões | 50 a 220 |

## Canal

| Código | Rótulo | Mídia no CAC |
| --- | --- | --- |
| `organic` | Orgânico | não |
| `referral` | Indicação | não |
| `google_ads` | Google Ads | sim |
| `linkedin_ads` | LinkedIn Ads | sim |
| `event` | Evento | sim, em março, junho, agosto e novembro |
| `outbound` | Outbound | sim (ferramenta e lista, não salário) |
| `partner` | Parceiro | sim (custo de programa) |
| `email` | E-mail | sim |

## Planos

`essencial`, `profissional`, `enterprise`. O MRR inicial depende do par porte × plano (de R$ 149 a R$ 4.290). Setup, quando existe, é 1× ou 2× o MRR e **não entra no MRR**. ACV = MRR × 12 + setup.

## Tabelas operacionais

Gravadas em `data/raw/` e no DuckDB `data/warehouse/crm.duckdb`.

### params

Uma linha. `as_of_date`, `period_start`, `period_end`, `gross_margin`, `seed`, `currency`, `vendor_name`, `product_name`.

### companies

Uma PME. `company_id`, `company_name`, `porte`, `sector`, `state_uf`, `city`, `employees`, `annual_revenue_brl`, `created_at`.

### contacts

Pessoas da PME. `role`: `decision_maker`, `champion`, `user`, `finance`. E-mail no domínio `exemplo-ficticio.test`. Telefone com DDD `00`.

### campaigns

Uma campanha por canal e mês. `spend_brl` pode ser zero.

### leads

Um lead por empresa. `mql_at` e `sql_at` nulos quando a etapa não aconteceu até a data de corte. `status`: `open`, `disqualified`, `mql`, `sql`, `opportunity`, `won`, `lost`.

### opportunities

No máximo uma por lead. `stage` é a etapa atual ou final (`qualificacao`, `proposta`, `negociacao`, `ganho`). `status`: `open`, `won`, `lost`. `probability` segue a etapa aberta (0,18 / 0,42 / 0,67) e vale 1 ou 0 quando o negócio fechou. `expected_close_date` pode passar da data de corte. `closed_at` não pode.

### opportunity_stages

Histórico. `stage_order` começa em 1. `exited_at` nulo na etapa em que o negócio ainda está. É esta tabela que alimenta o funil de etapas.

### subscriptions

Uma por ganho. `status` `active` ou `churned`. `end_date` é o primeiro mês **sem** fatura. `initial_mrr_brl` não muda. `current_mrr_brl` é o MRR vigente, ou zero se cancelou.

### mrr_movements

Um cliente-mês. Componentes da ponte: `beginning_mrr`, `new_mrr`, `expansion_mrr`, `contraction_mrr`, `churn_mrr`, `ending_mrr`. O mês de cancelamento tem `ending_mrr` zero e `churn_mrr` igual ao início. O mês de entrada tem `beginning_mrr` zero.

### invoices

`invoice_type`: `subscription` ou `setup`. `status`: `paid`, `open`, `overdue`. Meses anteriores ao último estão pagos, mesmo quando atrasaram. Outubro de 2026 ainda tem fatura aberta.

### churn_events

Um por assinatura cancelada. `reason`: `preco`, `produto`, `suporte`, `concorrente`, `encerrou_atividade`, `baixo_uso`. `mrr_lost` é o MRR do último mês ativo. `tenure_months` conta meses faturados.

### support_tickets

`priority`: `baixa`, `media`, `alta`, `urgente`. `category`: `duvida`, `cobranca`, `bug`, `implantacao`, `treinamento`, `indisponibilidade`. `csat` de 1 a 5, nulo se ainda está aberto. `resolution_hours` nulo no aberto.

## Estrela

`dim_*` carrega o rótulo em português (`channel_name`, `porte_name`, e assim por diante). `fact_*` guarda código e medida. `date_key` liga em `dim_date`. `dim_company.status`: `prospect`, `active`, `churned`. `cohort_month` só existe para quem comprou.

`fact_lead` traz flags `is_mql`, `is_sql`, `is_opportunity`, `is_won` para o funil não precisar de quatro fatos.

`fact_mrr_month` está no grão cliente × mês, com a ponte inteira. Some os componentes e só então divida.

`fact_opportunity.weighted_acv` já é `acv_brl * probability`.

`fact_invoice.days_late` é nulo quando a fatura não foi paga.

## Segmento RFM

| Código | Regra, nessa ordem |
| --- | --- |
| `champion` | R ≥ 4, F ≥ 4 e M ≥ 4 |
| `at_risk` | R ≤ 2, F ≥ 3 e M ≥ 3 |
| `recent` | R ≥ 4 e F ≤ 2 |
| `loyal` | F ≥ 4 e M ≥ 3 |
| `hibernating` | R ≤ 2 e F ≤ 2 |
| `promising` | R ≥ 3 e F ≥ 3 |
| `regular` | o resto |

R é recência (menos dias = nota maior). F é quantidade de faturas de assinatura pagas. M é a soma delas.

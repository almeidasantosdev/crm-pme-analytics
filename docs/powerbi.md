# O mesmo dashboard no Power BI

Não há arquivo `.pbix` de propósito. O modelo abaixo reconstrói as quatro páginas (Funil, Receita, Retenção, Segmentação) a partir dos CSV em `data/warehouse/star/`. A base continua fictícia.

## 1. Importar

Obter dados → Texto/CSV, ou Pasta apontando para `data/warehouse/star`.

Marque a primeira linha como cabeçalho. `date_key` é inteiro `AAAAMMDD`. `month_start` e `full_date` são data. Não deixe o Power BI promover `porte_code` a número.

Relacione **muitos para um**, com filtro cruzado simples, da fato para a dimensão:

| Fato | Coluna | Dimensão |
| --- | --- | --- |
| fact_lead | date_key | dim_date |
| fact_lead | company_id | dim_company |
| fact_lead | channel_code | dim_channel |
| fact_lead | porte_code | dim_porte |
| fact_lead | sector_code | dim_sector |
| fact_lead | campaign_id | dim_campaign |
| fact_opportunity | date_key | dim_date |
| fact_opportunity | company_id | dim_company |
| fact_opportunity | channel_code | dim_channel |
| fact_opportunity | porte_code | dim_porte |
| fact_opportunity | plan_code | dim_plan |
| fact_opportunity | stage_code | dim_stage |
| fact_opportunity | loss_reason_code | dim_loss_reason |
| fact_mrr_month | date_key | dim_date |
| fact_mrr_month | company_id | dim_company |
| fact_mrr_month | channel_code | dim_channel |
| fact_mrr_month | porte_code | dim_porte |
| fact_mrr_month | plan_code | dim_plan |
| fact_invoice | date_key | dim_date |
| fact_invoice | company_id | dim_company |
| fact_ticket | opened_date_key | dim_date |
| fact_ticket | company_id | dim_company |
| fact_churn | date_key | dim_date |
| fact_churn | company_id | dim_company |
| fact_churn | reason_code | dim_churn_reason |
| fact_churn | channel_code | dim_channel |
| fact_churn | porte_code | dim_porte |

`fact_opportunity` também tem `close_date_key` e `expected_close_date_key`. Deixe esses relacionamentos **inativos**. Dois caminhos ativos até `dim_date` deixam a medida ambígua. Para o pipeline, use `USERELATIONSHIP` na data esperada, como na medida lá embaixo.

Confira a cardinalidade: cada `company_id` aparece uma vez em `dim_company`. Se o Power BI reclamar de duplicata, a carga não é a deste repositório.

## 2. Armadilhas antes das medidas

**Não some `ending_mrr` no tempo.** MRR é foto. A soma de doze meses não é receita do ano e não é ARR. ARR de run-rate é o MRR do mês selecionado vezes 12.

**Não faça média de taxa.** Conversão do trimestre é a soma dos ganhos dividida pela soma dos leads. A média das taxas mensais mente quando o volume muda.

**CAC vazio não é zero.** Orgânico e indicação têm investimento 0. A medida devolve branco, não R$ 0.

**NRR e GRR não incluem cliente novo.** O denominador é o MRR do início do mês.

## 3. Medidas

Crie uma tabela vazia `Medidas` só para organizá-las, se quiser. As fórmulas assumem o mês no contexto de filtro (uma seleção, ou `MAX` da data visível).

```dax
Leads = COUNTROWS(fact_lead)

MQLs = CALCULATE(COUNTROWS(fact_lead), fact_lead[is_mql] = TRUE())

SQLs = CALCULATE(COUNTROWS(fact_lead), fact_lead[is_sql] = TRUE())

Oportunidades = CALCULATE(COUNTROWS(fact_lead), fact_lead[is_opportunity] = TRUE())

Ganhos = CALCULATE(COUNTROWS(fact_lead), fact_lead[is_won] = TRUE())

Lead para ganho = DIVIDE([Ganhos], [Leads])
```

`DIVIDE` devolve branco se o denominador for 0. Formate as taxas como porcentagem.

```dax
MRR =
VAR Mes = MAX(dim_date[month_start])
RETURN
CALCULATE(
    SUM(fact_mrr_month[ending_mrr]),
    fact_mrr_month[month_start] = Mes
)

ARR = [MRR] * 12

MRR inicial =
VAR Mes = MAX(dim_date[month_start])
RETURN CALCULATE(SUM(fact_mrr_month[beginning_mrr]), fact_mrr_month[month_start] = Mes)

MRR novo =
VAR Mes = MAX(dim_date[month_start])
RETURN CALCULATE(SUM(fact_mrr_month[new_mrr]), fact_mrr_month[month_start] = Mes)

MRR expansao =
VAR Mes = MAX(dim_date[month_start])
RETURN CALCULATE(SUM(fact_mrr_month[expansion_mrr]), fact_mrr_month[month_start] = Mes)

MRR contracao =
VAR Mes = MAX(dim_date[month_start])
RETURN CALCULATE(SUM(fact_mrr_month[contraction_mrr]), fact_mrr_month[month_start] = Mes)

MRR churn =
VAR Mes = MAX(dim_date[month_start])
RETURN CALCULATE(SUM(fact_mrr_month[churn_mrr]), fact_mrr_month[month_start] = Mes)

NRR = DIVIDE([MRR inicial] + [MRR expansao] - [MRR contracao] - [MRR churn], [MRR inicial])

GRR = DIVIDE([MRR inicial] - [MRR contracao] - [MRR churn], [MRR inicial])
```

Para um gráfico de linha no tempo, **não** use `[MRR]` do jeito acima dentro de um eixo mês se o `MAX` pegar só o último mês do visual inteiro. No gráfico, o contexto de cada ponto já é o mês. A versão para o eixo é a soma direta, porque cada ponto filtra um `month_start`:

```dax
MRR no ponto = SUM(fact_mrr_month[ending_mrr])

NRR no ponto =
DIVIDE(
    SUM(fact_mrr_month[beginning_mrr]) + SUM(fact_mrr_month[expansion_mrr])
        - SUM(fact_mrr_month[contraction_mrr]) - SUM(fact_mrr_month[churn_mrr]),
    SUM(fact_mrr_month[beginning_mrr])
)
```

Use `MRR no ponto` e `NRR no ponto` nos visuais temporais. Use `MRR` e `NRR` nos cartões, em que o contexto é o mês escolhido no segmentador. Se o segmentador deixar vários meses marcados, o cartão `MRR` fica no último mês visível (`MAX`). É o comportamento certo para uma foto. Escreva isso no subtítulo do cartão.

Churn de logos: a fato mensal não traz a contagem de clientes. Duas saídas. A mais simples é uma coluna calculada não — é uma medida sobre a fato filtrada:

```dax
Clientes no fim =
VAR Mes = MAX(dim_date[month_start])
RETURN
CALCULATE(
    DISTINCTCOUNT(fact_mrr_month[company_id]),
    fact_mrr_month[month_start] = Mes,
    fact_mrr_month[ending_mrr] > 0
)

Clientes no inicio =
VAR Mes = MAX(dim_date[month_start])
RETURN
CALCULATE(
    DISTINCTCOUNT(fact_mrr_month[company_id]),
    fact_mrr_month[month_start] = Mes,
    fact_mrr_month[beginning_mrr] > 0
)

Cancelados =
VAR Mes = MAX(dim_date[month_start])
RETURN
CALCULATE(
    DISTINCTCOUNT(fact_mrr_month[company_id]),
    fact_mrr_month[month_start] = Mes,
    fact_mrr_month[churn_mrr] > 0
)

Churn de logos = DIVIDE([Cancelados], [Clientes no inicio])

Churn de receita = DIVIDE([MRR churn], [MRR inicial])
```

CAC. O investimento está em `dim_campaign`, não na fato de MRR. Não relacione campanha e MRR por mês sem pensar: o ganho pode cair meses depois do lead. Nesta base o CAC do estudo é do período inteiro, first-touch, e o canal do cliente está em `dim_company[acquisition_channel_code]`.

```dax
Investimento = SUM(dim_campaign[spend_brl])

Clientes novos = CALCULATE(COUNTROWS(dim_company), dim_company[status] <> "prospect")

CAC =
IF(
    [Investimento] <= 0,
    BLANK(),
    DIVIDE([Investimento], [Clientes novos])
)
```

Com o segmentador de canal, as duas medidas respeitam o canal porque `dim_campaign[channel_code]` e `dim_company[acquisition_channel_code]` apontam para `dim_channel`. Confira se os dois relacionamentos estão ativos. Se o Power BI recusar o segundo caminho, calcule o CAC numa tabela importada de `sql/02_cac_by_channel.sql` (exporte o resultado para CSV). É mais curto e evita o caminho ambíguo. Eu faria assim num projeto de verdade: a consulta já é a definição.

Pipeline, usando a data esperada:

```dax
ACV ponderado =
CALCULATE(
    SUM(fact_opportunity[weighted_acv]),
    fact_opportunity[status] = "open",
    USERELATIONSHIP(fact_opportunity[expected_close_date_key], dim_date[date_key])
)
```

Coorte: `dim_company[cohort_month]` é o mês de entrada. Uma matriz com coorte nas linhas e a idade nas colunas pede a idade calculada. Sem uma fato de retenção pronta, o caminho mais fiel é importar o resultado de `sql/04_cohort_retention.sql` como tabela `cohort_retention` e montar a matriz `logo_retention` com coorte × `age_months`. Não tire a média dessa coluna: use

```dax
Retencao de logos =
DIVIDE(
    SUM(cohort_retention[active_customers]),
    SUM(cohort_retention[cohort_customers])
)
```

e repita a lógica para `retained_mrr / cohort_initial_mrr`.

RFM: importe `sql/06_rfm_segmentation.sql` como `rfm`. Segmento nas legendas, soma de `monetary` nos valores, contagem de `company_id` como cartão. LTV por porte: importe `sql/07_ltv.sql`. Não coloque `expected_ltv` de `sql/14_ltv_by_segment.sql` num cartão de meta. Aquela consulta existe para mostrar a fórmula quebrando.

## 4. Páginas

**Funil.** Funil de `Leads`, `MQLs`, `SQLs`, `Oportunidades`, `Ganhos`. Barras de `Lead para ganho` por `dim_channel[channel_name]`. Tabela de CAC ao lado, com os canais de investimento zero aparecendo em branco. Segmentadores: canal, porte, ano (`dim_date[year]`).

**Receita.** Cartões de MRR, ARR, NRR e GRR. Gráfico de colunas empilhadas com novos, expansão, contração negativa e churn negativo. Linha de NRR e GRR com uma linha constante em 1. Subtítulo: "foto do mês, não soma".

**Retenção.** Matriz de coorte (mapa de calor). Linha de churn de logos e de receita. Barras de `fact_churn[mrr_lost]` por `dim_churn_reason[reason_name]`.

**Segmentação.** Barras de receita histórica por segmento. Colunas agrupadas de LTV histórico e esperado por porte. Caixa de texto com a premissa da margem de 80% e a censura à direita.

Formato de moeda: real, zero casas nos cartões de MRR, uma casa na porcentagem.

## 5. O que conferir antes de publicar

- Cartão de MRR de outubro/2026 perto de R$ 425 mil, não na casa dos milhões. Se estiver na casa dos milhões, a medida somou os meses.
- NRR de outubro perto de 99%, não de um número enorme. Se passou de 2, a medida somou NRR ou dividiu pelo cliente errado.
- Orgânico e indicação sem valor de CAC.
- Funil com ganho menor que oportunidade, menor que SQL, menor que MQL, menor que lead.
- Idade 0 da coorte em 100%.

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
from common import (
    CORAL,
    TEAL,
    banner,
    chart_layout,
    choose_filters,
    db_token,
    fmt_pct,
    inject_css,
    load,
    month_labels,
    sidebar,
    subset,
)

from analysis.metrics import rollup_cohort, rollup_mrr

inject_css()
sidebar()
banner()
token = db_token()
cohort = load("04_cohort_retention.sql", token)
mrr = load("03_mrr_arr_nrr.sql", token)
reasons = load("10_churn_reasons.sql", token)

channel, porte, year = choose_filters(cohort, date_column="cohort_month")
view = subset(cohort, channel, porte, year, date_column="cohort_month")
rolled = rollup_cohort(view)
rolled = rolled[rolled["age_months"] <= 18]
monthly = rollup_mrr(subset(mrr, channel, porte, None))
monthly = monthly[monthly["beginning_customers"] >= 30]

st.title("Retenção e coortes")
st.caption("Idade 0 é o mês de entrada. Retenção de receita pode passar de 100% quando há expansão.")

if rolled.empty:
    st.warning("O recorte não tem coorte.")
else:
    pivot = rolled.pivot(index="cohort_month", columns="age_months", values="logo_retention")
    pivot.index = month_labels(pivot.index.to_series())
    fig = px.imshow(
        pivot,
        color_continuous_scale=["#F7F1E6", "#8FBFAE", "#0F6E62"],
        origin="upper",
        zmin=0.45,
        zmax=1,
        aspect="auto",
        labels={"color": "Logos"},
    )
    fig.update_layout(**chart_layout("Retenção de logos"))
    fig.update_coloraxes(colorbar_tickformat=".0%")
    st.plotly_chart(fig, use_container_width=True)

    ages = rolled.groupby("age_months", as_index=False)[
        ["cohort_customers", "active_customers", "cohort_initial_mrr", "retained_mrr"]
    ].sum()
    ages["logo"] = ages["active_customers"] / ages["cohort_customers"]
    ages["receita"] = ages["retained_mrr"] / ages["cohort_initial_mrr"]
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=ages["age_months"], y=ages["logo"], name="Logos", line={"color": CORAL, "width": 2.2}))
    fig.add_trace(
        go.Scatter(x=ages["age_months"], y=ages["receita"], name="Receita", line={"color": TEAL, "width": 2.2})
    )
    fig.update_layout(**chart_layout("Curva média das coortes do recorte", "Retenção"))
    fig.update_yaxes(tickformat=".0%")
    st.plotly_chart(fig, use_container_width=True)
    st.caption("A curva média pondera pelo tamanho da coorte. Coorte recente ainda não chegou nas idades altas.")

if len(monthly):
    labels = month_labels(monthly["month_start"])
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=labels, y=monthly["logo_churn_rate"], name="Logos", line={"color": CORAL, "width": 2}))
    fig.add_trace(
        go.Scatter(x=labels, y=monthly["revenue_churn_rate"], name="Receita", line={"color": TEAL, "width": 2})
    )
    fig.update_layout(**chart_layout("Churn mensal, meses com pelo menos 30 clientes no início", "Taxa"))
    fig.update_yaxes(tickformat=".1%")
    st.plotly_chart(fig, use_container_width=True)
    st.caption("O denominador é a base do início do mês. Cliente novo não entra e não cancela no mês de entrada.")

st.subheader("Motivo do cancelamento")
st.caption("Motivo declarado na saída. O MRR perdido é o do último mês ativo, não a vida inteira do cliente.")
fig = go.Figure(
    go.Bar(
        x=reasons["reason_name"],
        y=reasons["mrr_lost"],
        marker_color="#A34545",
        text=[fmt_pct(value / reasons["mrr_lost"].sum()) for value in reasons["mrr_lost"]],
        textposition="outside",
    )
)
fig.update_layout(**chart_layout("MRR perdido por motivo", "R$"))
st.plotly_chart(fig, use_container_width=True)

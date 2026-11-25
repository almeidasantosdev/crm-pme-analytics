import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import plotly.graph_objects as go
import streamlit as st
from common import (
    GOLD,
    TEAL,
    banner,
    chart_layout,
    choose_filters,
    db_token,
    fmt_brl_short,
    fmt_num,
    fmt_pct,
    inject_css,
    load,
    month_labels,
    sidebar,
    subset,
)

from analysis.metrics import rollup_funnel, rollup_mrr

inject_css()
sidebar()
banner()
st_token = db_token()
funnel = load("01_funnel_conversion.sql", st_token)
mrr = load("03_mrr_arr_nrr.sql", st_token)
pipeline = load("08_pipeline_forecast.sql", st_token)

channel, porte, year = choose_filters(funnel)
funnel_view = subset(funnel, channel, porte, year)
mrr_view = subset(mrr, channel, porte, year)
monthly = rollup_mrr(mrr_view)
latest = monthly.dropna(subset=["nrr"]).iloc[-1]
totals = rollup_funnel(funnel_view)
weighted = float(subset(pipeline, channel, porte, None, date_column="close_month")["weighted_acv"].sum())

st.title("CRM da Nexora, em uma página")
st.caption(
    "Software de gestão para PME. O crescimento desta base vem de logo novo: a retenção líquida fica abaixo de 100%."
)

c1, c2, c3, c4, c5 = st.columns(5)
c1.metric("Clientes ativos", fmt_num(latest.ending_customers))
c2.metric("MRR", fmt_brl_short(latest.ending_mrr))
c3.metric("ARR de run-rate", fmt_brl_short(latest.ending_arr))
c4.metric("NRR do mês", fmt_pct(latest.nrr))
c5.metric("Pipeline ponderado", fmt_brl_short(weighted))

left, right = st.columns(2)
with left:
    labels = month_labels(monthly["month_start"])
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=labels, y=monthly["ending_mrr"], name="MRR", line={"color": TEAL, "width": 2.4}))
    fig.update_layout(**chart_layout("MRR no fim do mês", "R$"))
    st.plotly_chart(fig, use_container_width=True)
with right:
    stages = ["Lead", "MQL", "SQL", "Oportunidade", "Ganho"]
    values = [totals["leads"], totals["mqls"], totals["sqls"], totals["opportunities"], totals["wins"]]
    fig = go.Figure(
        go.Funnel(
            y=stages,
            x=values,
            textinfo="value+percent initial",
            marker={"color": [TEAL, "#1F6F78", "#3E8F78", GOLD, "#143F45"]},
        )
    )
    fig.update_layout(**chart_layout("Funil do recorte"))
    st.plotly_chart(fig, use_container_width=True)

st.info(
    f"De cada 100 leads do recorte, {fmt_pct(totals['lead_to_win'])} viram cliente. "
    f"O NRR de {fmt_pct(latest.nrr)} diz que a base já existente, sozinha, não segura o MRR: "
    "expansão não cobre contração e cancelamento."
)

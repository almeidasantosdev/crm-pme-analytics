import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import plotly.graph_objects as go
import streamlit as st
from common import (
    CORAL,
    GOLD,
    TEAL,
    banner,
    chart_layout,
    choose_filters,
    db_token,
    fmt_brl,
    fmt_num,
    fmt_pct,
    inject_css,
    load,
    month_labels,
    sidebar,
    subset,
)

from analysis.metrics import rollup_mrr

inject_css()
sidebar()
banner()
mrr = load("03_mrr_arr_nrr.sql", db_token())
channel, porte, year = choose_filters(mrr)
monthly = rollup_mrr(subset(mrr, channel, porte, year))
closed = monthly[monthly["beginning_mrr"] > 0]
latest = monthly.iloc[-1]

st.title("Receita recorrente")
st.caption("MRR é foto do fim do mês. Somar o MRR de vários meses não é receita do período.")

c1, c2, c3, c4 = st.columns(4)
c1.metric("MRR", fmt_brl(latest.ending_mrr))
c2.metric("ARR de run-rate", fmt_brl(latest.ending_arr))
c3.metric("NRR", fmt_pct(latest.nrr))
c4.metric("GRR", fmt_pct(latest.grr))

labels = month_labels(monthly["month_start"])
fig = go.Figure()
fig.add_bar(name="Novos", x=labels, y=monthly["new_mrr"], marker_color=TEAL)
fig.add_bar(name="Expansão", x=labels, y=monthly["expansion_mrr"], marker_color=GOLD)
fig.add_bar(name="Contração", x=labels, y=-monthly["contraction_mrr"], marker_color="#C4A46A")
fig.add_bar(name="Cancelamento", x=labels, y=-monthly["churn_mrr"], marker_color=CORAL)
fig.update_layout(barmode="relative", **chart_layout("Ponte de MRR", "R$"))
st.plotly_chart(fig, use_container_width=True)

row = latest
fig = go.Figure(
    go.Bar(
        x=["Novos", "Expansão", "Contração", "Cancelamento"],
        y=[row.new_mrr, row.expansion_mrr, row.contraction_mrr, row.churn_mrr],
        marker_color=[TEAL, GOLD, "#C4A46A", CORAL],
        text=[fmt_brl(value) for value in (row.new_mrr, row.expansion_mrr, row.contraction_mrr, row.churn_mrr)],
        textposition="outside",
    )
)
fig.update_layout(**chart_layout("Movimentos do último mês do recorte", "R$"))
st.plotly_chart(fig, use_container_width=True)
st.caption(
    f"O mês abre em {fmt_brl(row.beginning_mrr)} e fecha em {fmt_brl(row.ending_mrr)}. "
    "Os quatro movimentos cabem nesse intervalo; por isso não vão na mesma escala do estoque."
)

nrr_labels = month_labels(closed["month_start"])
fig = go.Figure()
fig.add_trace(go.Scatter(x=nrr_labels, y=closed["nrr"], name="NRR", line={"color": TEAL, "width": 2.2}))
fig.add_trace(go.Scatter(x=nrr_labels, y=closed["grr"], name="GRR", line={"color": GOLD, "width": 2}))
fig.add_hline(y=1, line_dash="dash", line_color="#B7A99A")
fig.update_layout(**chart_layout("Retenção de receita", "Índice"))
fig.update_yaxes(tickformat=".0%")
st.plotly_chart(fig, use_container_width=True)
st.caption("NRR inclui expansão. GRR não. Os dois usam a base do início do mês, sem o cliente novo.")

table = monthly.tail(12).copy()
table["Mês"] = month_labels(table["month_start"])
table = table[
    ["Mês", "ending_customers", "ending_mrr", "new_mrr", "expansion_mrr", "contraction_mrr", "churn_mrr", "nrr", "grr"]
]
st.dataframe(
    table.rename(
        columns={
            "ending_customers": "Clientes",
            "ending_mrr": "MRR",
            "new_mrr": "Novos",
            "expansion_mrr": "Expansão",
            "contraction_mrr": "Contração",
            "churn_mrr": "Cancelamento",
            "nrr": "NRR",
            "grr": "GRR",
        }
    ).style.format(
        {
            "Clientes": lambda v: fmt_num(v),
            "MRR": lambda v: fmt_brl(v),
            "Novos": lambda v: fmt_brl(v),
            "Expansão": lambda v: fmt_brl(v),
            "Contração": lambda v: fmt_brl(v),
            "Cancelamento": lambda v: fmt_brl(v),
            "NRR": lambda v: fmt_pct(v),
            "GRR": lambda v: fmt_pct(v),
        }
    ),
    use_container_width=True,
    hide_index=True,
)

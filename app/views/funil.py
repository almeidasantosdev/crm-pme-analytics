import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import plotly.graph_objects as go
import streamlit as st
from common import (
    PALETTE,
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
    sidebar,
    stage_name,
    subset,
)

from analysis.labels import CHANNEL
from analysis.metrics import campaign_cac, rollup_funnel

inject_css()
sidebar()
banner()
token = db_token()
funnel = load("01_funnel_conversion.sql", token)
stages = load("09_opportunity_stages.sql", token)
cac = load("02_cac_by_channel.sql", token)
cycle = load("12_sales_cycle.sql", token)

channel, porte, year = choose_filters(funnel)
view = subset(funnel, channel, porte, year)
totals = rollup_funnel(view)
stage_view = stages.copy()
if channel != "Todos":
    stage_view = stage_view[stage_view["channel"] == channel]
if porte != "Todos":
    stage_view = stage_view[stage_view["porte"] == porte]
reached = stage_view.groupby("stage", as_index=False)["opportunities_reached"].sum() if len(stage_view) else stage_view

st.title("Funil e custo de aquisição")
st.caption("Etapas aninhadas. A taxa do período é a soma dos volumes, não a média das taxas mensais.")

c1, c2, c3, c4 = st.columns(4)
c1.metric("Lead → MQL", fmt_pct(totals["lead_to_mql"]))
c2.metric("MQL → SQL", fmt_pct(totals["mql_to_sql"]))
c3.metric("SQL → oportunidade", fmt_pct(totals["sql_to_opportunity"]))
c4.metric("Oportunidade → ganho", fmt_pct(totals["opportunity_to_win"]))

order = ["qualificacao", "proposta", "negociacao", "ganho"]
if len(reached):
    reached["order"] = reached["stage"].map({name: index for index, name in enumerate(order)})
    reached = reached.sort_values("order")
    fig = go.Figure(
        go.Bar(
            x=[stage_name(item) for item in reached["stage"]],
            y=reached["opportunities_reached"],
            marker_color=TEAL,
            text=reached["opportunities_reached"],
            textposition="outside",
        )
    )
    fig.update_layout(**chart_layout("Oportunidades que chegaram a cada etapa", "Oportunidades"))
    st.plotly_chart(fig, use_container_width=True)
    st.caption("Histórico de etapas, não a etapa atual. Um ganho já passou por proposta e negociação.")

by_channel = view.groupby("channel", as_index=False)[["leads", "wins"]].sum()
by_channel["rate"] = by_channel["wins"] / by_channel["leads"]
by_channel = by_channel.sort_values("rate", ascending=False)
fig = go.Figure(
    go.Bar(
        x=[CHANNEL[item] for item in by_channel["channel"]],
        y=by_channel["rate"],
        marker_color=PALETTE[: len(by_channel)],
        text=[fmt_pct(value) for value in by_channel["rate"]],
        textposition="outside",
    )
)
fig.update_layout(**chart_layout("Conversão lead → ganho por canal"))
fig.update_yaxes(tickformat=".0%", range=[0, max(by_channel["rate"].max() * 1.25, 0.05)])
st.plotly_chart(fig, use_container_width=True)

st.subheader("CAC de campanha")
st.caption(
    "Investimento de mídia dividido pelos clientes do canal. Orgânico e indicação "
    "ficam sem CAC: não houve mídia, e o custo comercial não está na conta."
)
table = cac.copy()
if channel != "Todos":
    table = table[table["channel"] == channel]
table["canal"] = table["channel"].map(CHANNEL)
table["cac"] = [campaign_cac(row.spend_brl, row.new_customers) for row in table.itertuples(index=False)]
table["leitura"] = ["amostra curta" if row.new_customers < 10 else "ok" for row in table.itertuples(index=False)]
show = table[table["new_customers"] >= 10]
show = show[show["cac"].notna()].sort_values("payback_months")
if len(show):
    fig = go.Figure(
        go.Bar(
            x=show["canal"],
            y=show["payback_months"],
            marker_color="#A9782F",
            text=[f"{value:.1f} meses".replace(".", ",") for value in show["payback_months"]],
            textposition="outside",
        )
    )
    fig.update_layout(**chart_layout("Payback da mídia, em meses de MRR inicial", "Meses"))
    st.plotly_chart(fig, use_container_width=True)

pretty = table[["canal", "spend_brl", "new_customers", "avg_initial_mrr", "cac", "payback_months", "leitura"]].rename(
    columns={
        "spend_brl": "Investimento",
        "new_customers": "Clientes",
        "avg_initial_mrr": "MRR inicial",
        "cac": "CAC",
        "payback_months": "Payback (meses)",
        "leitura": "Leitura",
        "canal": "Canal",
    }
)
st.dataframe(
    pretty.style.format(
        {
            "Investimento": lambda v: fmt_brl(v),
            "MRR inicial": lambda v: fmt_brl(v),
            "CAC": lambda v: fmt_brl(v),
            "Payback (meses)": lambda v: "—" if v != v else f"{v:.1f}".replace(".", ","),
            "Clientes": lambda v: fmt_num(v),
        }
    ),
    use_container_width=True,
    hide_index=True,
)

st.caption("Ciclo mediano, em dias, só dos ganhos. Canal com poucos ganhos oscila.")
cycle_view = cycle.copy()
if channel != "Todos":
    cycle_view = cycle_view[cycle_view["channel"] == channel]
cycle_view["canal"] = cycle_view["channel"].map(CHANNEL)
cycle_view["median_cycle_days"] = cycle_view["median_cycle_days"].round(0)
cycle_view["avg_cycle_days"] = cycle_view["avg_cycle_days"].round(1)
st.dataframe(
    cycle_view[["canal", "wins", "median_cycle_days", "avg_cycle_days"]].rename(
        columns={
            "canal": "Canal",
            "wins": "Ganhos",
            "median_cycle_days": "Mediana (dias)",
            "avg_cycle_days": "Média (dias)",
        }
    ),
    use_container_width=True,
    hide_index=True,
)

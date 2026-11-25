import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import plotly.graph_objects as go
import streamlit as st
from common import (
    GOLD,
    ROOT,
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
    subset,
)

inject_css()
sidebar()
banner()
token = db_token()
rfm = load("06_rfm_segmentation.sql", token)
ltv = load("07_ltv.sql", token)
segment_ltv = load("14_ltv_by_segment.sql", token)

channel, porte, _year = choose_filters(rfm, with_year=False)
view = subset(rfm, channel, porte, None)

st.title("Segmentação e valor")
st.caption("RFM da receita recorrente paga. Fatura de setup fica de fora.")

if view.empty:
    st.warning("O recorte não tem cliente com fatura paga.")
else:
    summary = (
        view.groupby(["segment_code", "segment_name"], as_index=False)
        .agg(clientes=("company_id", "count"), receita=("monetary", "sum"), mrr_medio=("monetary", "mean"))
        .sort_values("receita", ascending=False)
    )
    c1, c2, c3 = st.columns(3)
    c1.metric("Clientes no RFM", fmt_num(len(view)))
    c2.metric("Receita paga no recorte", fmt_brl(view["monetary"].sum()))
    c3.metric("Recência mediana (dias)", fmt_num(view["recency_days"].median()))

    fig = go.Figure(
        go.Bar(
            x=summary["segment_name"],
            y=summary["receita"],
            marker_color=TEAL,
            text=[fmt_num(value) + " clientes" for value in summary["clientes"]],
            textposition="outside",
        )
    )
    fig.update_layout(**chart_layout("Receita histórica por segmento", "R$"))
    st.plotly_chart(fig, use_container_width=True)

st.subheader("LTV por porte")
st.caption(
    "O histórico é o que já foi faturado e está censurado: cliente novo ainda não viveu a vida toda. "
    "O esperado é ARPU × margem / churn mensal, com churn constante e sem expansão futura."
)
ltv_view = ltv if porte == "Todos" else ltv[ltv["porte"] == porte]
fig = go.Figure()
fig.add_bar(name="Histórico", x=ltv_view["porte_name"], y=ltv_view["avg_historical_ltv"], marker_color=TEAL)
fig.add_bar(name="Esperado", x=ltv_view["porte_name"], y=ltv_view["expected_ltv"], marker_color=GOLD)
fig.update_layout(barmode="group", **chart_layout("LTV médio por porte", "R$"))
st.plotly_chart(fig, use_container_width=True)
st.caption(
    "Média empresa: o esperado fica bem acima do histórico porque o churn mensal é baixo "
    "e muita gente da coorte ainda está ativa. Não é caixa já realizado."
)

with st.expander("Por que o LTV esperado por segmento RFM engana"):
    st.write(
        "Campeão e leal são definidos por ainda pagarem. O churn dentro do recorte vai a zero "
        "e a fórmula ARPU / churn dispara. Compare os segmentos pelo histórico."
    )
    st.dataframe(
        segment_ltv[["segment_name", "customers", "avg_historical_ltv", "monthly_churn_rate", "expected_ltv"]]
        .rename(
            columns={
                "segment_name": "Segmento",
                "customers": "Clientes",
                "avg_historical_ltv": "LTV histórico",
                "monthly_churn_rate": "Churn mensal",
                "expected_ltv": "LTV esperado",
            }
        )
        .style.format(
            {
                "Clientes": lambda v: fmt_num(v),
                "LTV histórico": lambda v: fmt_brl(v),
                "Churn mensal": lambda v: fmt_pct(v, 2),
                "LTV esperado": lambda v: fmt_brl(v),
            }
        ),
        use_container_width=True,
        hide_index=True,
    )

st.subheader("Propensão a cancelar em 90 dias")
report_path = ROOT / "outputs" / "churn_model.json"
if not report_path.exists():
    st.info("Rode `make analysis` para gravar a avaliação do modelo.")
else:
    report = json.loads(report_path.read_text(encoding="utf-8"))
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("AUC logística", f"{report['logistic_roc_auc']:.2f}".replace(".", ","))
    c2.metric("AUC da árvore", f"{report['gradient_boosting_roc_auc']:.2f}".replace(".", ","))
    c3.metric("AUC da regra", f"{report['rule_roc_auc']:.2f}".replace(".", ","))
    c4.metric("Precisão no teste", fmt_pct(report["test_precision"]))
    low, high = report["logistic_roc_auc_ci95"]
    st.caption(
        f"IC 95% do AUC, bootstrap: {low:.2f}–{high:.2f}. "
        f"Teste com {report['test_positives']} cancelamentos em {report['test_rows']} fotos "
        f"(taxa base {fmt_pct(report['test_positive_rate'])}). "
        f"O corte de probabilidade foi escolhido no treino."
    )
    importance = report["logistic_importance"][:6]
    fig = go.Figure(
        go.Bar(
            x=[row["importance"] for row in importance][::-1],
            y=[row["feature"] for row in importance][::-1],
            orientation="h",
            marker_color=TEAL,
        )
    )
    fig.update_layout(**chart_layout("Peso relativo na logística", "Fração da soma dos |coef.|"))
    st.plotly_chart(fig, use_container_width=True)
    unseen = report["unseen_company_auc"]
    unseen_text = ""
    if unseen is not None:
        unseen_label = f"{unseen:.2f}".replace(".", ",")
        unseen_text = f"Só entre empresas inéditas, o AUC cai para {unseen_label}. "
    st.warning(
        "Isto não é um modelo de produção. O gerador planta um rastro (mais chamados e atraso) "
        "em parte de quem vai cancelar, e parte sai em silêncio. "
        f"No teste, {report['companies_in_both_splits']} empresas também aparecem no treino, em data anterior. "
        f"{unseen_text}"
        "A soma dos coeficientes infla variável com muitas categorias, como canal."
    )

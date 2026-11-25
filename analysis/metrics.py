"""Fórmulas de receita usadas no app e nos testes.

As consultas em sql/ são a referência comentada. Estas funções existem
para o recorte interativo (canal, porte, ano) sem recalcular taxa em
cima de taxa.
"""

from __future__ import annotations

import pandas as pd


def net_revenue_retention(
    beginning: float,
    expansion: float,
    contraction: float,
    churn: float,
) -> float | None:
    """NRR = (início + expansão - contração - churn) / início."""
    if beginning == 0:
        return None
    return (beginning + expansion - contraction - churn) / beginning


def gross_revenue_retention(beginning: float, contraction: float, churn: float) -> float | None:
    """GRR ignora expansão. Com a identidade de MRR correta, não passa de 1."""
    if beginning == 0:
        return None
    return (beginning - contraction - churn) / beginning


def quick_ratio(new: float, expansion: float, contraction: float, churn: float) -> float | None:
    lost = contraction + churn
    if lost == 0:
        return None
    return (new + expansion) / lost


def campaign_cac(spend: float, new_customers: float) -> float | None:
    """CAC nulo quando não há mídia rastreada ou quando não houve cliente."""
    if spend <= 0 or new_customers <= 0:
        return None
    return spend / new_customers


def rollup_funnel(frame: pd.DataFrame) -> dict[str, float]:
    leads = float(frame["leads"].sum())
    mqls = float(frame["mqls"].sum())
    sqls = float(frame["sqls"].sum())
    opportunities = float(frame["opportunities"].sum())
    wins = float(frame["wins"].sum())

    def ratio(numerator: float, denominator: float) -> float | None:
        if denominator == 0:
            return None
        return numerator / denominator

    return {
        "leads": leads,
        "mqls": mqls,
        "sqls": sqls,
        "opportunities": opportunities,
        "wins": wins,
        "lead_to_mql": ratio(mqls, leads),
        "mql_to_sql": ratio(sqls, mqls),
        "sql_to_opportunity": ratio(opportunities, sqls),
        "opportunity_to_win": ratio(wins, opportunities),
        "lead_to_win": ratio(wins, leads),
    }


def rollup_mrr(frame: pd.DataFrame) -> pd.DataFrame:
    columns = [
        "beginning_mrr",
        "new_mrr",
        "expansion_mrr",
        "contraction_mrr",
        "churn_mrr",
        "ending_mrr",
        "beginning_customers",
        "new_customers",
        "churned_customers",
        "ending_customers",
    ]
    grouped = frame.groupby("month_start", as_index=False)[columns].sum()
    grouped["ending_arr"] = grouped["ending_mrr"] * 12
    grouped["nrr"] = [
        net_revenue_retention(row.beginning_mrr, row.expansion_mrr, row.contraction_mrr, row.churn_mrr)
        for row in grouped.itertuples(index=False)
    ]
    grouped["grr"] = [
        gross_revenue_retention(row.beginning_mrr, row.contraction_mrr, row.churn_mrr)
        for row in grouped.itertuples(index=False)
    ]
    grouped["quick_ratio"] = [
        quick_ratio(row.new_mrr, row.expansion_mrr, row.contraction_mrr, row.churn_mrr)
        for row in grouped.itertuples(index=False)
    ]
    grouped["logo_churn_rate"] = grouped["churned_customers"] / grouped["beginning_customers"].where(
        grouped["beginning_customers"] > 0
    )
    grouped["revenue_churn_rate"] = grouped["churn_mrr"] / grouped["beginning_mrr"].where(grouped["beginning_mrr"] > 0)
    return grouped.sort_values("month_start")


def rollup_cohort(frame: pd.DataFrame) -> pd.DataFrame:
    """Soma fatias e recalcula a retenção. Não tira média das taxas."""
    grouped = frame.groupby(["cohort_month", "age_months"], as_index=False)[
        ["cohort_customers", "active_customers", "cohort_initial_mrr", "retained_mrr"]
    ].sum()
    grouped["logo_retention"] = grouped["active_customers"] / grouped["cohort_customers"]
    grouped["revenue_retention"] = grouped["retained_mrr"] / grouped["cohort_initial_mrr"]
    return grouped.sort_values(["cohort_month", "age_months"])


def apply_filters(
    frame: pd.DataFrame,
    channel: str | None = None,
    porte: str | None = None,
    year: int | None = None,
    date_column: str = "month_start",
) -> pd.DataFrame:
    filtered = frame
    if channel and channel != "Todos" and "channel" in filtered.columns:
        filtered = filtered[filtered["channel"] == channel]
    if porte and porte != "Todos" and "porte" in filtered.columns:
        filtered = filtered[filtered["porte"] == porte]
    if year and date_column in filtered.columns:
        filtered = filtered[filtered[date_column].dt.year == year]
    return filtered

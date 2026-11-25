"""Figuras estáticas para o README, a partir das consultas SQL."""

from __future__ import annotations

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd
from matplotlib.colors import LinearSegmentedColormap

from analysis.labels import CHANNEL, PORTE
from analysis.metrics import rollup_cohort, rollup_mrr
from analysis.queries import ROOT, run_sql_file

INK = "#1C2430"
TEAL = "#0F6E62"
GOLD = "#A9782F"
CORAL = "#A34545"
GRID = "#E4DDD2"
CMAP = LinearSegmentedColormap.from_list("nexora", ["#F7F1E6", "#8FBFAE", "#0F6E62"])


def _style() -> None:
    plt.rcParams.update(
        {
            "font.family": "DejaVu Sans",
            "axes.edgecolor": "#D9D0C3",
            "axes.labelcolor": INK,
            "xtick.color": INK,
            "ytick.color": INK,
            "text.color": INK,
            "axes.titleweight": "regular",
            "figure.facecolor": "white",
            "axes.facecolor": "white",
            "axes.spines.top": False,
            "axes.spines.right": False,
        }
    )


def _save(fig: plt.Figure, name: str) -> None:
    folder = ROOT / "docs" / "figures"
    folder.mkdir(parents=True, exist_ok=True)
    fig.tight_layout()
    fig.savefig(folder / name, dpi=140)
    plt.close(fig)


def funnel_chart() -> None:
    detail = run_sql_file("01_funnel_conversion.sql")
    by_channel = detail.groupby("channel", as_index=False)[["leads", "wins"]].sum().sort_values("wins", ascending=False)
    by_channel["rate"] = by_channel["wins"] / by_channel["leads"]
    by_channel["label"] = by_channel["channel"].map(CHANNEL)
    fig, ax = plt.subplots(figsize=(8.2, 4.6))
    ax.barh(by_channel["label"], by_channel["rate"] * 100, color=TEAL)
    ax.set_xlabel("Lead → ganho (%)")
    ax.set_title("Conversão do funil por canal")
    ax.invert_yaxis()
    _save(fig, "funil_canal.png")


def mrr_chart() -> None:
    monthly = rollup_mrr(run_sql_file("03_mrr_arr_nrr.sql"))
    fig, ax = plt.subplots(figsize=(8.4, 4.6))
    ax.plot(monthly["month_start"], monthly["ending_mrr"] / 1000, color=TEAL, linewidth=2.2, label="MRR")
    ax.set_ylabel("MRR (R$ mil)")
    ax.set_title("MRR e retenção líquida de receita")
    ax2 = ax.twinx()
    ax2.plot(monthly["month_start"], monthly["nrr"] * 100, color=GOLD, linewidth=1.6, label="NRR")
    ax2.axhline(100, color="#B7A99A", linewidth=0.8, linestyle="--")
    ax2.set_ylabel("NRR (%)")
    ax2.spines["top"].set_visible(False)
    lines, labels = ax.get_legend_handles_labels()
    lines2, labels2 = ax2.get_legend_handles_labels()
    ax.legend(lines + lines2, labels + labels2, frameon=False, loc="upper left")
    _save(fig, "mrr_nrr.png")


def cohort_chart() -> None:
    cohort = rollup_cohort(run_sql_file("04_cohort_retention.sql"))
    cohort = cohort[cohort["age_months"] <= 18]
    pivot = cohort.pivot(index="cohort_month", columns="age_months", values="logo_retention")
    fig, ax = plt.subplots(figsize=(8.6, 6.2))
    image = ax.imshow(pivot.to_numpy(), aspect="auto", cmap=CMAP, vmin=0.4, vmax=1)
    ax.set_xticks(range(len(pivot.columns)))
    ax.set_xticklabels(pivot.columns)
    labels = [pd.Timestamp(value).strftime("%Y-%m") for value in pivot.index]
    ax.set_yticks(range(len(labels)))
    ax.set_yticklabels(labels, fontsize=7)
    ax.set_xlabel("Idade da coorte (meses)")
    ax.set_title("Retenção de logos por coorte")
    fig.colorbar(image, ax=ax, fraction=0.03, pad=0.02)
    _save(fig, "coorte_retencao.png")


def churn_chart() -> None:
    monthly = rollup_mrr(run_sql_file("03_mrr_arr_nrr.sql"))
    monthly = monthly[monthly["beginning_customers"] > 0]
    fig, ax = plt.subplots(figsize=(8.4, 4.4))
    ax.plot(monthly["month_start"], monthly["logo_churn_rate"] * 100, color=CORAL, linewidth=2, label="Logos")
    ax.plot(
        monthly["month_start"],
        monthly["revenue_churn_rate"] * 100,
        color=TEAL,
        linewidth=2,
        label="Receita",
    )
    ax.set_ylabel("Churn no mês (%)")
    ax.set_title("Cancelamento mensal")
    ax.legend(frameon=False)
    _save(fig, "churn_mensal.png")


def ltv_chart() -> None:
    ltv = run_sql_file("07_ltv.sql")
    ltv["label"] = ltv["porte"].map(PORTE)
    fig, ax = plt.subplots(figsize=(7.6, 4.6))
    positions = range(len(ltv))
    width = 0.36
    ax.bar(
        [item - width / 2 for item in positions],
        ltv["avg_historical_ltv"] / 1000,
        width=width,
        color=TEAL,
        label="Histórico",
    )
    ax.bar(
        [item + width / 2 for item in positions],
        ltv["expected_ltv"] / 1000,
        width=width,
        color=GOLD,
        label="Esperado",
    )
    ax.set_xticks(list(positions))
    ax.set_xticklabels(ltv["label"])
    ax.set_ylabel("R$ mil")
    ax.set_title("LTV por porte")
    ax.legend(frameon=False)
    _save(fig, "ltv_porte.png")


def main() -> None:
    _style()
    funnel_chart()
    mrr_chart()
    cohort_chart()
    churn_chart()
    ltv_chart()
    print("Figuras em", ROOT / "docs" / "figures")


if __name__ == "__main__":
    main()

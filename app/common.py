"""Peças visuais compartilhadas do dashboard."""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import streamlit as st

APP_DIR = Path(__file__).resolve().parent
ROOT = APP_DIR.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from analysis.labels import CHANNEL, MONTH_PT, PORTE, SEGMENT, STAGE
from analysis.metrics import apply_filters
from analysis.queries import DEFAULT_DB, run_sql_file

TEAL = "#0F6E62"
TEAL_DARK = "#143F45"
GOLD = "#A9782F"
CORAL = "#A34545"
BLUE = "#3E6A86"
INK = "#1C2430"
PALETTE = [TEAL, TEAL_DARK, GOLD, BLUE, CORAL, "#6E8B74", "#C4A46A", "#7A5C45"]


def inject_css() -> None:
    st.markdown(
        """
        <style>
        .stApp { background: #F3F0E8; }
        [data-testid="stSidebar"] { background: #143F45; }
        [data-testid="stSidebar"] * { color: #F4F1EA; }
        [data-testid="stSidebar"] [data-testid="stSelectbox"] input {
            color: #1C2430 !important;
            -webkit-text-fill-color: #1C2430 !important;
            background: #FFFdf8 !important;
        }
        [data-testid="stSidebar"] [data-testid="stSelectbox"] button {
            color: #1C2430 !important;
        }
        [data-testid="stHeader"], [data-testid="stToolbar"] { display: none; }
        h1, h2, h3 { letter-spacing: -0.02em; }
        .banner {
            background: #FFFdf8;
            border: 1px solid #E4DDD2;
            border-left: 4px solid #0F6E62;
            padding: 0.7rem 0.9rem;
            border-radius: 8px;
            margin-bottom: 0.8rem;
            color: #1C2430;
        }
        [data-testid="stMetric"] {
            background: #FFFdf8;
            border: 1px solid #E4DDD2;
            border-top: 3px solid #0F6E62;
            padding: 0.55rem 0.75rem 0.35rem;
            border-radius: 10px;
        }
        [data-testid="stMetricLabel"] { color: #5C675E; }
        footer, #MainMenu { visibility: hidden; }
        </style>
        """,
        unsafe_allow_html=True,
    )


def sidebar() -> None:
    st.sidebar.markdown("### Nexora Gestão")
    st.sidebar.caption("Analytics de CRM para PME")
    st.sidebar.markdown("Base **fictícia** · semente 42")
    st.sidebar.caption("Corte em 31/10/2026. A Nexora não existe.")


@st.cache_data(show_spinner=False)
def load(filename: str, token: float) -> pd.DataFrame:
    del token
    return run_sql_file(filename)


def db_token() -> float:
    return DEFAULT_DB.stat().st_mtime


def banner() -> None:
    st.markdown(
        '<div class="banner">Dados gerados por <code>data/generate.py</code>. '
        "Não há empresa, pessoa ou fatura real nesta base.</div>",
        unsafe_allow_html=True,
    )


def fmt_brl(value: float | None, digits: int = 0) -> str:
    if value is None or pd.isna(value):
        return "—"
    sign = "-" if value < 0 else ""
    number = f"{abs(value):,.{digits}f}"
    number = number.replace(",", "X").replace(".", ",").replace("X", ".")
    return f"{sign}R$ {number}"


def fmt_pct(value: float | None, digits: int = 1) -> str:
    if value is None or pd.isna(value):
        return "—"
    return f"{value * 100:.{digits}f}%".replace(".", ",")


def fmt_brl_short(value: float | None) -> str:
    if value is None or pd.isna(value):
        return "—"
    sign = "-" if value < 0 else ""
    amount = abs(value)
    if amount >= 1_000_000:
        text = f"{amount / 1_000_000:.1f}".replace(".", ",")
        return f"{sign}R$ {text} mi"
    if amount >= 10_000:
        return f"{sign}R$ {amount / 1000:.0f} mil"
    return fmt_brl(value)


def fmt_num(value: float | None, digits: int = 0) -> str:
    if value is None or pd.isna(value):
        return "—"
    return f"{value:,.{digits}f}".replace(",", "X").replace(".", ",").replace("X", ".")


def month_labels(values: pd.Series) -> list[str]:
    labels = []
    for value in values:
        stamp = pd.Timestamp(value)
        labels.append(f"{MONTH_PT[stamp.month - 1]}/{stamp.year}")
    return labels


def channel_name(code: str) -> str:
    return "Todos" if code == "Todos" else CHANNEL.get(code, code)


def porte_name(code: str) -> str:
    return "Todos" if code == "Todos" else PORTE.get(code, code)


def stage_name(code: str) -> str:
    return STAGE.get(code, code)


def segment_name(code: str) -> str:
    return SEGMENT.get(code, code)


def choose_filters(
    frame: pd.DataFrame,
    date_column: str | None = "month_start",
    with_year: bool = True,
) -> tuple[str, str, int | None]:
    channels = sorted(frame["channel"].dropna().unique()) if "channel" in frame.columns else []
    portes = [code for code in PORTE if "porte" in frame.columns and code in set(frame["porte"])]
    years: list[int] = []
    if with_year and date_column and date_column in frame.columns:
        years = sorted(int(year) for year in frame[date_column].dt.year.dropna().unique())
    st.sidebar.markdown("### Recorte")
    channel = st.sidebar.selectbox("Canal", ["Todos", *channels], format_func=channel_name)
    porte = st.sidebar.selectbox("Porte", ["Todos", *portes], format_func=porte_name)
    year = None
    if years:
        picked = st.sidebar.selectbox("Ano", ["Todos", *[str(item) for item in years]])
        year = None if picked == "Todos" else int(picked)
    return channel, porte, year


def subset(
    frame: pd.DataFrame,
    channel: str,
    porte: str,
    year: int | None,
    date_column: str = "month_start",
) -> pd.DataFrame:
    return apply_filters(frame, channel=channel, porte=porte, year=year, date_column=date_column)


def chart_layout(title: str, y_title: str | None = None) -> dict[str, object]:
    return {
        "title": {"text": title, "font": {"size": 16, "color": INK}},
        "paper_bgcolor": "rgba(0,0,0,0)",
        "plot_bgcolor": "rgba(0,0,0,0)",
        "font": {"color": INK, "family": "DejaVu Sans, sans-serif"},
        "margin": {"l": 48, "r": 24, "t": 52, "b": 48},
        "legend": {"orientation": "h", "y": -0.22},
        "yaxis": {"gridcolor": "#E4DDD2", "title": y_title or ""},
        "xaxis": {"title": ""},
    }

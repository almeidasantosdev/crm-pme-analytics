"""Executa os arquivos de sql/ contra o DuckDB da base fictícia."""

from __future__ import annotations

from pathlib import Path

import duckdb
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DB = ROOT / "data" / "warehouse" / "crm.duckdb"
SQL_DIR = ROOT / "sql"

DATE_COLUMNS = {
    "month_start",
    "cohort_month",
    "close_month",
    "last_paid_at",
    "as_of_date",
    "period_start",
    "period_end",
    "created_at",
    "start_date",
    "end_date",
    "churn_date",
}


def metric_sql_files() -> list[str]:
    return sorted(path.name for path in SQL_DIR.glob("[0-9]*.sql"))


def run_sql_file(filename: str, db_path: Path | None = None) -> pd.DataFrame:
    sql = (SQL_DIR / filename).read_text(encoding="utf-8")
    connection = duckdb.connect(str(db_path or DEFAULT_DB), read_only=True)
    try:
        frame = connection.execute(sql).df()
    finally:
        connection.close()
    for column in DATE_COLUMNS.intersection(frame.columns):
        frame[column] = pd.to_datetime(frame[column])
    return frame


def run_sql(sql: str, db_path: Path | None = None) -> pd.DataFrame:
    connection = duckdb.connect(str(db_path or DEFAULT_DB), read_only=True)
    try:
        return connection.execute(sql).df()
    finally:
        connection.close()

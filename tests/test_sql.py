import duckdb
import pandas as pd
import pytest

from analysis.queries import ROOT, metric_sql_files, run_sql_file


def test_schema_creates_operational_tables(tmp_path):
    connection = duckdb.connect(str(tmp_path / "empty.duckdb"))
    connection.execute((ROOT / "sql" / "schema.sql").read_text(encoding="utf-8"))
    tables = {row[0] for row in connection.execute("SHOW TABLES").fetchall()}
    for name in ("leads", "opportunities", "mrr_movements", "churn_events", "params"):
        assert name in tables


@pytest.mark.parametrize("filename", metric_sql_files())
def test_metric_query_runs(filename: str):
    frame = run_sql_file(filename)
    assert len(frame.columns) > 0
    if filename != "11_data_quality.sql":
        assert len(frame) > 0


def test_data_quality_has_no_violations():
    quality = run_sql_file("11_data_quality.sql")
    assert (quality["violations"] == 0).all()


def test_cac_is_blank_without_spend_and_matches_the_ratio():
    cac = run_sql_file("02_cac_by_channel.sql")
    organic = cac.loc[cac["channel"] == "organic"].iloc[0]
    assert organic.spend_brl == 0
    assert pd.isna(organic.cac_brl)
    paid = cac[cac["spend_brl"] > 0]
    assert (paid["new_customers"] > 0).all()
    assert (paid["cac_brl"] - paid["spend_brl"] / paid["new_customers"]).abs().max() < 0.02


def test_opportunity_stage_counts_do_not_grow():
    stages = run_sql_file("09_opportunity_stages.sql")
    totals = stages.groupby("stage")["opportunities_reached"].sum()
    assert totals["qualificacao"] >= totals["proposta"] >= totals["negociacao"] >= totals["ganho"]


def test_pipeline_is_only_open_and_weighted_does_not_exceed_nominal():
    pipeline = run_sql_file("08_pipeline_forecast.sql")
    assert (pipeline["weighted_acv"] <= pipeline["pipeline_acv"] + 0.02).all()
    assert pipeline["deals"].sum() > 0


def test_expected_ltv_by_porte_is_finite():
    ltv = run_sql_file("07_ltv.sql")
    assert set(ltv["porte"]) == {"mei", "micro", "pequena", "media"}
    assert (ltv["expected_ltv"] > 0).all()
    assert (ltv["monthly_churn_rate"] > 0).all()
    assert (ltv["expected_ltv"] > ltv["avg_historical_ltv"]).all()

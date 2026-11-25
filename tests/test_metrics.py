import math

import pandas as pd
import pytest

from analysis.metrics import (
    campaign_cac,
    gross_revenue_retention,
    net_revenue_retention,
    quick_ratio,
    rollup_cohort,
    rollup_funnel,
    rollup_mrr,
)
from analysis.queries import run_sql, run_sql_file


def test_nrr_and_grr_formulas():
    assert net_revenue_retention(100, 10, 5, 8) == pytest.approx(0.97)
    assert gross_revenue_retention(100, 5, 8) == pytest.approx(0.87)
    assert net_revenue_retention(0, 10, 0, 0) is None
    assert quick_ratio(20, 10, 5, 5) == pytest.approx(3)
    assert campaign_cac(0, 10) is None
    assert campaign_cac(1000, 4) == pytest.approx(250)


def test_rollup_matches_sql_month_nrr():
    detail = run_sql_file("03_mrr_arr_nrr.sql")
    rolled = rollup_mrr(detail).dropna(subset=["nrr"])
    direct = run_sql(
        """
        SELECT month_start,
               (SUM(beginning_mrr) + SUM(expansion_mrr) - SUM(contraction_mrr) - SUM(churn_mrr))
                   / NULLIF(SUM(beginning_mrr), 0) AS nrr
        FROM mrr_movements
        GROUP BY 1
        HAVING SUM(beginning_mrr) > 0
        ORDER BY 1
        """
    )
    direct["month_start"] = pd.to_datetime(direct["month_start"])
    merged = rolled.merge(direct, on="month_start", suffixes=("_py", "_sql"))
    assert len(merged) == len(direct)
    assert (merged["nrr_py"] - merged["nrr_sql"]).abs().max() < 1e-9


def test_funnel_rollup_is_not_an_average_of_rates():
    detail = run_sql_file("01_funnel_conversion.sql")
    totals = rollup_funnel(detail)
    assert totals["wins"] <= totals["opportunities"] <= totals["sqls"] <= totals["mqls"] <= totals["leads"]
    assert totals["lead_to_win"] == pytest.approx(totals["wins"] / totals["leads"])
    assert not math.isclose(totals["lead_to_win"], detail["lead_to_win"].mean())


def test_cohort_age_zero_is_full_retention():
    cohort = rollup_cohort(run_sql_file("04_cohort_retention.sql"))
    age_zero = cohort[cohort["age_months"] == 0]
    assert (age_zero["logo_retention"] - 1).abs().max() < 1e-9
    assert (age_zero["revenue_retention"] - 1).abs().max() < 1e-9

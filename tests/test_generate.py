import pandas as pd

from data.generate import ROOT, generate


def test_same_seed_reproduces_identifiers():
    first = generate(write=False)
    second = generate(write=False)
    assert first["leads"]["lead_id"].tolist() == second["leads"]["lead_id"].tolist()
    assert first["companies"]["company_name"].tolist() == second["companies"]["company_name"].tolist()
    assert first["mrr_movements"]["ending_mrr"].sum() == second["mrr_movements"]["ending_mrr"].sum()


def test_checked_in_extract_matches_the_script():
    fresh = generate(write=False)
    leads = pd.read_csv(ROOT / "data" / "raw" / "leads.csv")
    subscriptions = pd.read_csv(ROOT / "data" / "raw" / "subscriptions.csv")
    assert fresh["leads"]["lead_id"].tolist() == leads["lead_id"].tolist()
    assert fresh["subscriptions"]["initial_mrr_brl"].sum() == pytest_approx(subscriptions["initial_mrr_brl"].sum())


def pytest_approx(value: float):
    import pytest

    return pytest.approx(value)


def test_contacts_are_obviously_fake(fresh_frames):
    contacts = fresh_frames["contacts"]
    assert contacts["email"].str.endswith("@exemplo-ficticio.test").all()
    assert contacts["phone"].str.startswith("+55 00 ").all()


def test_funnel_flags_are_nested(fresh_frames):
    leads = fresh_frames["leads"]
    opportunities = fresh_frames["opportunities"]
    assert leads["sql_at"].notna().sum() <= leads["mql_at"].notna().sum()
    assert opportunities["lead_id"].nunique() == len(opportunities)
    won = set(opportunities.loc[opportunities["status"] == "won", "lead_id"])
    sql_leads = set(leads.loc[leads["sql_at"].notna(), "lead_id"])
    assert won <= sql_leads
    assert set(fresh_frames["subscriptions"]["opportunity_id"]) == set(
        opportunities.loc[opportunities["status"] == "won", "opportunity_id"]
    )


def test_mrr_identity(fresh_frames):
    movements = fresh_frames["mrr_movements"]
    ending = (
        movements["beginning_mrr"]
        + movements["new_mrr"]
        + movements["expansion_mrr"]
        - movements["contraction_mrr"]
        - movements["churn_mrr"]
    )
    assert (movements["ending_mrr"] - ending).abs().max() < 0.02


def test_star_files_match_operational_counts():
    leads = pd.read_csv(ROOT / "data" / "raw" / "leads.csv")
    fact_lead = pd.read_csv(ROOT / "data" / "warehouse" / "star" / "fact_lead.csv")
    movements = pd.read_csv(ROOT / "data" / "raw" / "mrr_movements.csv")
    fact_mrr = pd.read_csv(ROOT / "data" / "warehouse" / "star" / "fact_mrr_month.csv")
    assert len(fact_lead) == len(leads)
    assert len(fact_mrr) == len(movements)

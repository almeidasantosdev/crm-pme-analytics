from datetime import date, timedelta

from analysis.churn_model import FORBIDDEN_FEATURES, TEST_SNAPSHOTS, TRAIN_SNAPSHOTS, evaluate


def test_split_leaves_a_gap_after_the_label_window():
    last_train = max(TRAIN_SNAPSHOTS)
    first_test = min(TEST_SNAPSHOTS)
    assert first_test >= last_train + timedelta(days=90)
    assert max(TEST_SNAPSHOTS) + timedelta(days=90) <= date(2026, 10, 31)


def test_model_beats_chance_and_does_not_leak():
    result = evaluate()
    assert FORBIDDEN_FEATURES.isdisjoint(result["features"])
    assert result["test_positives"] >= 20
    assert 0.68 <= result["logistic_roc_auc"] <= 0.90
    assert result["logistic_roc_auc"] > result["rule_roc_auc"]
    assert result["logistic_brier"] < result["baseline_brier"]
    assert 0 < result["test_precision"] < 1
    assert result["test_recall"] > 0
    low, high = result["logistic_roc_auc_ci95"]
    assert low < result["logistic_roc_auc"] < high

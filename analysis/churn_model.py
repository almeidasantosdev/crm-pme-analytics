"""Propensão a cancelar em 90 dias, com corte no tempo.

O fator de risco que o gerador usa para sortear tickets, atraso e
cancelamento não entra aqui. As variáveis são as que um analista veria
no CRM na data da foto: plano, porte, canal, MRR, tickets, CSAT e faturas.

A foto de teste é posterior à janela de rótulo do treino. Cancelamento
depois da data de corte não existe na base, então o horizonte de 90 dias
termina antes de 31/10/2026.
"""

from __future__ import annotations

import json
from datetime import date
from pathlib import Path

import duckdb
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import GradientBoostingClassifier
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    average_precision_score,
    brier_score_loss,
    confusion_matrix,
    precision_recall_fscore_support,
    roc_auc_score,
    roc_curve,
)
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

from analysis.queries import DEFAULT_DB, ROOT

TRAIN_SNAPSHOTS = (
    date(2024, 6, 30),
    date(2024, 12, 31),
    date(2025, 6, 30),
    date(2025, 9, 30),
)
TEST_SNAPSHOTS = (date(2026, 3, 31), date(2026, 6, 30))
HORIZON_DAYS = 90
# Setor ficou de fora: são doze níveis e a soma dos coeficientes parecia
# importância alta sem melhorar o AUC no teste. Plano permanece porque o
# preço muda junto com o porte e o leitor espera ver os dois.
CATEGORICAL = ["porte", "plan", "channel"]
NUMERIC = [
    "tenure_months",
    "mrr",
    "employees",
    "annual_revenue_brl",
    "tickets_90d",
    "avg_csat_90d",
    "csat_missing",
    "late_invoices_180d",
    "had_expansion",
    "lifetime_paid",
]
FORBIDDEN_FEATURES = {
    "churn_date",
    "end_date",
    "reason",
    "risk",
    "frailty",
    "mrr_lost",
    "status",
}


def load_tables(db_path: Path) -> dict[str, pd.DataFrame]:
    connection = duckdb.connect(str(db_path), read_only=True)
    try:
        names = [
            "companies",
            "subscriptions",
            "mrr_movements",
            "invoices",
            "support_tickets",
            "churn_events",
        ]
        return {name: connection.execute(f"SELECT * FROM {name}").df() for name in names}
    finally:
        connection.close()


def _as_of(value: date) -> pd.Timestamp:
    return pd.Timestamp(value)


def build_observation_frame(tables: dict[str, pd.DataFrame]) -> pd.DataFrame:
    companies = tables["companies"].set_index("company_id")
    subscriptions = tables["subscriptions"].set_index("company_id")
    movements = tables["mrr_movements"].copy()
    invoices = tables["invoices"].copy()
    tickets = tables["support_tickets"].copy()
    churn = tables["churn_events"].set_index("company_id")

    movements["month_start"] = pd.to_datetime(movements["month_start"])
    invoices["issued_at"] = pd.to_datetime(invoices["issued_at"])
    invoices["due_at"] = pd.to_datetime(invoices["due_at"])
    invoices["paid_at"] = pd.to_datetime(invoices["paid_at"])
    tickets["opened_at"] = pd.to_datetime(tickets["opened_at"])
    subscriptions = subscriptions.copy()
    subscriptions["start_date"] = pd.to_datetime(subscriptions["start_date"])

    rows: list[dict[str, object]] = []
    for snapshot in (*TRAIN_SNAPSHOTS, *TEST_SNAPSHOTS):
        snap = _as_of(snapshot)
        month_start = pd.Timestamp(date(snapshot.year, snapshot.month, 1))
        active = movements[(movements["month_start"] == month_start) & (movements["ending_mrr"] > 0)]
        window_start = snap - pd.Timedelta(days=90)
        late_start = snap - pd.Timedelta(days=180)
        horizon = snap + pd.Timedelta(days=HORIZON_DAYS)
        split = "train" if snapshot in TRAIN_SNAPSHOTS else "test"

        for company_id, movement in active.set_index("company_id").iterrows():
            company = companies.loc[company_id]
            subscription = subscriptions.loc[company_id]
            company_tickets = tickets[tickets["company_id"] == company_id]
            recent_tickets = company_tickets[
                (company_tickets["opened_at"] > window_start) & (company_tickets["opened_at"] <= snap)
            ]
            csat = recent_tickets["csat"].dropna()
            company_invoices = invoices[
                (invoices["company_id"] == company_id) & (invoices["invoice_type"] == "subscription")
            ]
            known_invoices = company_invoices[company_invoices["issued_at"] <= snap]
            in_late_window = known_invoices[known_invoices["issued_at"] > late_start]
            paid_late = (
                in_late_window["paid_at"].notna()
                & (in_late_window["paid_at"] <= snap)
                & (in_late_window["paid_at"] > in_late_window["due_at"])
            )
            open_late = (in_late_window["paid_at"].isna() | (in_late_window["paid_at"] > snap)) & (
                in_late_window["due_at"] < snap
            )
            paid_known = known_invoices[known_invoices["paid_at"].notna() & (known_invoices["paid_at"] <= snap)]
            history = movements[(movements["company_id"] == company_id) & (movements["month_start"] <= month_start)]
            churn_date = pd.to_datetime(churn.at[company_id, "churn_date"]) if company_id in churn.index else pd.NaT
            label = int(pd.notna(churn_date) and snap < churn_date <= horizon)
            tenure = (month_start.year - subscription.start_date.year) * 12 + (
                month_start.month - subscription.start_date.month
            )
            rows.append(
                {
                    "company_id": company_id,
                    "snapshot_date": snap,
                    "split": split,
                    "label": label,
                    "porte": company.porte,
                    "sector": company.sector,
                    "plan": subscription.plan,
                    "channel": subscription.channel,
                    "employees": int(company.employees),
                    "annual_revenue_brl": float(company.annual_revenue_brl),
                    "tenure_months": int(tenure),
                    "mrr": float(movement.ending_mrr),
                    "tickets_90d": int(len(recent_tickets)),
                    "avg_csat_90d": float(csat.mean()) if len(csat) else np.nan,
                    "csat_missing": int(len(csat) == 0),
                    "late_invoices_180d": int((paid_late | open_late).sum()),
                    "had_expansion": int((history["expansion_mrr"] > 0).any()),
                    "lifetime_paid": float(paid_known["amount_brl"].sum()),
                }
            )
    frame = pd.DataFrame(rows)
    leaked = FORBIDDEN_FEATURES.intersection(frame.columns)
    if leaked:
        raise RuntimeError(f"Vazamento de variável: {sorted(leaked)}")
    return frame


def _estimator(kind: str) -> Pipeline:
    preprocess = ColumnTransformer(
        transformers=[
            (
                "num",
                Pipeline(
                    [
                        ("impute", SimpleImputer(strategy="median")),
                        ("scale", StandardScaler()),
                    ]
                ),
                NUMERIC,
            ),
            (
                "cat",
                OneHotEncoder(handle_unknown="ignore", sparse_output=False),
                CATEGORICAL,
            ),
        ]
    )
    if kind == "logistic":
        model = LogisticRegression(max_iter=1000, random_state=42)
    elif kind == "gradient_boosting":
        model = GradientBoostingClassifier(
            random_state=42,
            max_depth=3,
            n_estimators=120,
            learning_rate=0.06,
        )
    else:
        raise ValueError(kind)
    return Pipeline([("prep", preprocess), ("model", model)])


def _best_f1_threshold(y_true: np.ndarray, scores: np.ndarray) -> float:
    thresholds = np.quantile(scores, np.linspace(0.05, 0.95, 19))
    best_threshold = 0.5
    best_f1 = -1.0
    for threshold in thresholds:
        precision, recall, f1, _ = precision_recall_fscore_support(
            y_true,
            scores >= threshold,
            average="binary",
            zero_division=0,
        )
        del precision, recall
        if f1 > best_f1:
            best_f1 = float(f1)
            best_threshold = float(threshold)
    return best_threshold


def _grouped_importance(pipeline: Pipeline, kind: str) -> list[dict[str, float | str]]:
    preprocessor: ColumnTransformer = pipeline.named_steps["prep"]
    names = list(preprocessor.get_feature_names_out())
    model = pipeline.named_steps["model"]
    if kind == "logistic":
        values = np.abs(model.coef_[0])
    else:
        values = model.feature_importances_
    grouped: dict[str, float] = {}
    for name, value in zip(names, values, strict=True):
        raw = name.split("__", 1)[1]
        key = raw
        for column in CATEGORICAL:
            if raw.startswith(f"{column}_"):
                key = column
                break
        grouped[key] = grouped.get(key, 0.0) + float(value)
    total = sum(grouped.values()) or 1.0
    ranking = [
        {"feature": feature, "importance": importance / total}
        for feature, importance in sorted(grouped.items(), key=lambda item: item[1], reverse=True)
    ]
    return ranking


def _bootstrap_auc(y_true: np.ndarray, scores: np.ndarray, draws: int = 400) -> tuple[float, float]:
    rng = np.random.default_rng(42)
    aucs: list[float] = []
    for _ in range(draws):
        index = rng.integers(0, len(y_true), len(y_true))
        if len(np.unique(y_true[index])) < 2:
            continue
        aucs.append(float(roc_auc_score(y_true[index], scores[index])))
    if not aucs:
        return (float("nan"), float("nan"))
    low, high = np.percentile(aucs, [2.5, 97.5])
    return float(low), float(high)


def evaluate(db_path: Path | None = None) -> dict[str, object]:
    tables = load_tables(db_path or DEFAULT_DB)
    frame = build_observation_frame(tables)
    train = frame[frame["split"] == "train"]
    test = frame[frame["split"] == "test"]
    features = CATEGORICAL + NUMERIC
    x_train = train[features]
    y_train = train["label"].to_numpy()
    x_test = test[features]
    y_test = test["label"].to_numpy()

    logistic = _estimator("logistic")
    boosting = _estimator("gradient_boosting")
    logistic.fit(x_train, y_train)
    boosting.fit(x_train, y_train)
    logistic_scores = logistic.predict_proba(x_test)[:, 1]
    boosting_scores = boosting.predict_proba(x_test)[:, 1]
    train_scores = logistic.predict_proba(x_train)[:, 1]
    threshold = _best_f1_threshold(y_train, train_scores)
    predicted = logistic_scores >= threshold
    precision, recall, f1, _ = precision_recall_fscore_support(y_test, predicted, average="binary", zero_division=0)
    matrix = confusion_matrix(y_test, predicted).tolist()
    train_rate = float(y_train.mean())
    baseline_scores = np.full_like(logistic_scores, train_rate, dtype=float)
    rule_scores = test["tickets_90d"].to_numpy() + 2 * test["late_invoices_180d"].to_numpy()
    auc_low, auc_high = _bootstrap_auc(y_test, logistic_scores)
    unseen = ~test["company_id"].isin(set(train["company_id"]))
    unseen_auc = None
    if unseen.sum() >= 30 and test.loc[unseen, "label"].nunique() == 2:
        unseen_auc = float(roc_auc_score(y_test[unseen.to_numpy()], logistic_scores[unseen.to_numpy()]))

    return {
        "target": "Cancelou nos 90 dias seguintes à foto",
        "horizon_days": HORIZON_DAYS,
        "train_snapshots": [item.isoformat() for item in TRAIN_SNAPSHOTS],
        "test_snapshots": [item.isoformat() for item in TEST_SNAPSHOTS],
        "features": features,
        "train_rows": int(len(train)),
        "test_rows": int(len(test)),
        "train_positive_rate": train_rate,
        "test_positive_rate": float(y_test.mean()),
        "test_positives": int(y_test.sum()),
        "companies_in_both_splits": int(len(set(train["company_id"]).intersection(test["company_id"]))),
        "unseen_company_auc": unseen_auc,
        "logistic_roc_auc": float(roc_auc_score(y_test, logistic_scores)),
        "logistic_roc_auc_ci95": [auc_low, auc_high],
        "logistic_average_precision": float(average_precision_score(y_test, logistic_scores)),
        "logistic_brier": float(brier_score_loss(y_test, logistic_scores)),
        "baseline_brier": float(brier_score_loss(y_test, baseline_scores)),
        "gradient_boosting_roc_auc": float(roc_auc_score(y_test, boosting_scores)),
        "gradient_boosting_average_precision": float(average_precision_score(y_test, boosting_scores)),
        "rule_roc_auc": float(roc_auc_score(y_test, rule_scores)),
        "threshold_selected_on_train": threshold,
        "test_precision": float(precision),
        "test_recall": float(recall),
        "test_f1": float(f1),
        "confusion_matrix": matrix,
        "logistic_importance": _grouped_importance(logistic, "logistic"),
        "curves": {
            "fpr": roc_curve(y_test, logistic_scores)[0].round(4).tolist(),
            "tpr": roc_curve(y_test, logistic_scores)[1].round(4).tolist(),
        },
        "frame": frame,
        "logistic_scores": logistic_scores,
        "y_test": y_test,
    }


def _write_figures(result: dict[str, object], figure_dir: Path) -> None:
    figure_dir.mkdir(parents=True, exist_ok=True)
    fpr = result["curves"]["fpr"]
    tpr = result["curves"]["tpr"]
    fig, ax = plt.subplots(figsize=(6.2, 5.2))
    ax.plot(fpr, tpr, color="#0F6E62", linewidth=2.2, label=f"Logística · AUC {result['logistic_roc_auc']:.2f}")
    ax.plot([0, 1], [0, 1], color="#B7A99A", linestyle="--", label="Aleatório")
    ax.set_xlabel("Falsos positivos")
    ax.set_ylabel("Verdadeiros positivos")
    ax.set_title("Propensão a cancelar · curva ROC no teste")
    ax.legend(frameon=False)
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    fig.tight_layout()
    fig.savefig(figure_dir / "churn_roc.png", dpi=140)
    plt.close(fig)

    importance = pd.DataFrame(result["logistic_importance"]).head(8).iloc[::-1]
    fig, ax = plt.subplots(figsize=(7.2, 4.6))
    ax.barh(importance["feature"], importance["importance"], color="#0F6E62")
    ax.set_xlabel("Peso relativo (soma dos |coeficientes| normalizada)")
    ax.set_title("O que a regressão logística usa para ordenar risco")
    fig.tight_layout()
    fig.savefig(figure_dir / "churn_importancia.png", dpi=140)
    plt.close(fig)


def write_report(db_path: Path | None = None, output_path: Path | None = None) -> dict[str, object]:
    result = evaluate(db_path)
    skip = {"frame", "logistic_scores", "y_test", "curves"}
    payload = {key: value for key, value in result.items() if key not in skip}
    payload["roc_curve"] = result["curves"]
    target = output_path or (ROOT / "outputs" / "churn_model.json")
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    _write_figures(result, ROOT / "docs" / "figures")
    return payload


def main() -> None:
    payload = write_report()
    print(
        "AUC logística "
        f"{payload['logistic_roc_auc']:.3f} "
        f"(IC95 {payload['logistic_roc_auc_ci95'][0]:.3f}–{payload['logistic_roc_auc_ci95'][1]:.3f}) "
        f"· GBM {payload['gradient_boosting_roc_auc']:.3f} "
        f"· regra {payload['rule_roc_auc']:.3f}"
    )
    print(
        f"Teste: {payload['test_positives']} cancelamentos em {payload['test_rows']} fotos "
        f"({payload['test_positive_rate']:.1%})."
    )


if __name__ == "__main__":
    main()

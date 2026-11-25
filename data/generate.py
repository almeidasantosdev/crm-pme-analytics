"""Gera a base fictícia de CRM da Nexora.

A Nexora é uma empresa inventada. Ela vende o software Nexora Gestão
(financeiro, propostas e atendimento) para PME brasileiras. Cada linha
desta base sai deste script. Não há extração de cliente, planilha
interna nem dado público de empresa real.

A semente padrão é 42. O mesmo comando reconstrói os mesmos arquivos.

    python data/generate.py

Regras de negócio da simulação (parâmetros, não medições):

- Um lead por empresa e atribuição first-touch. O canal do lead é o canal
  da oportunidade e da assinatura.
- As etapas são aninhadas: ganho implica oportunidade, que implica SQL,
  que implica MQL.
- A oportunidade só entra na base quando a data de abertura já chegou
  na data de corte. Negócios ainda no meio do ciclo ficam em aberto.
- A assinatura cobra mês a mês. O primeiro mês não cancela. Expansão e
  contração alteram o MRR; cancelamento zera a partir do mês seguinte
  ao último faturado.
- CAC de campanha usa só o investimento de mídia/programa. Orgânico e
  indicação ficam com investimento zero de propósito.
- Porte, canal e um fator de risco latente (não exportado) mudam a
  chance mensal de cancelar.
- Cerca de sete em cada dez cancelamentos deixam rastro nos dois meses
  anteriores: mais chamados, CSAT pior e fatura atrasada. Os outros saem
  em silêncio, e uma minoria de quem fica também abre chamado.
"""

from __future__ import annotations

import argparse
import json
import random
import unicodedata
from datetime import date, timedelta
from pathlib import Path

import duckdb
import pandas as pd

from analysis.labels import (
    CHANNEL,
    CHURN_REASON,
    LOSS_REASON,
    PLAN,
    PORTE,
    SECTOR,
    STAGE,
    UF_NAME,
)
from data.catalog import (
    CHANNEL_CONVERSION,
    CHANNEL_RISK,
    CHANNEL_SPEND,
    CHANNEL_WEIGHTS,
    CHANNELS,
    CITIES,
    EMPLOYEE_RANGE,
    EVENT_MONTHS,
    EVENT_SPEND,
    FIRST_NAMES,
    LAST_NAMES,
    MONTH_SEASON,
    NAME_CORES,
    NAME_PREFIXES,
    OWNERS,
    PLAN_MRR,
    PLAN_WEIGHTS,
    PORTE_RISK,
    PORTE_WEIGHTS,
    PORTE_WIN,
    REVENUE_RANGE,
    SECTOR_RISK,
    SECTOR_WEIGHTS,
    STAGE_PROBABILITY,
    UF_WEIGHTS,
)

ROOT = Path(__file__).resolve().parents[1]
AS_OF_DEFAULT = date(2026, 10, 31)
START_DEFAULT = date(2023, 1, 1)
GROSS_MARGIN = 0.80
VENDOR_NAME = "Nexora"
PRODUCT_NAME = "Nexora Gestão"

TRIAGE_DAYS = 30
MQL_FOLLOWUP_DAYS = 21
SQL_FOLLOWUP_DAYS = 14


def _pick(rng: random.Random, weights: dict[str, float] | tuple[tuple[str, float], ...]) -> str:
    if isinstance(weights, dict):
        options = list(weights)
        values = [weights[item] for item in options]
    else:
        options = [item[0] for item in weights]
        values = [item[1] for item in weights]
    return rng.choices(options, weights=values, k=1)[0]


def _add_months(month_start: date, count: int) -> date:
    index = month_start.month - 1 + count
    year = month_start.year + index // 12
    month = index % 12 + 1
    return date(year, month, 1)


def _month_starts(start: date, end: date) -> list[date]:
    cursor = date(start.year, start.month, 1)
    last = date(end.year, end.month, 1)
    months: list[date] = []
    while cursor <= last:
        months.append(cursor)
        cursor = _add_months(cursor, 1)
    return months


def _month_end_span(month_start: date) -> int:
    return (_add_months(month_start, 1) - month_start).days


def _random_day(rng: random.Random, month_start: date) -> date:
    return month_start + timedelta(days=rng.randrange(_month_end_span(month_start)))


def _slug(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value)
    ascii_text = "".join(char for char in normalized if not unicodedata.combining(char))
    return "".join(char for char in ascii_text.lower() if char.isalnum())


def _date_key(value: date | None) -> int | None:
    if value is None:
        return None
    return value.year * 10000 + value.month * 100 + value.day


def _money(cents: int) -> float:
    return round(cents / 100, 2)


def _frame(rows: list[dict[str, object]]) -> pd.DataFrame:
    return pd.DataFrame(rows)


def _lead_status(
    created: date,
    mql_at: date | None,
    sql_at: date | None,
    opp_status: str | None,
    as_of: date,
    rng: random.Random,
) -> tuple[str, str | None]:
    if opp_status == "won":
        return "won", None
    if opp_status == "lost":
        return "lost", None
    if opp_status == "open":
        return "opportunity", None
    if sql_at is not None:
        if (as_of - sql_at).days > SQL_FOLLOWUP_DAYS:
            reason = _pick(rng, {"sem_budget": 40, "sem_timing": 35, "sem_autoridade": 25})
            return "disqualified", reason
        return "sql", None
    if mql_at is not None:
        if (as_of - mql_at).days > MQL_FOLLOWUP_DAYS:
            reason = _pick(rng, {"sem_budget": 34, "sem_timing": 40, "sem_autoridade": 26})
            return "disqualified", reason
        return "mql", None
    if (as_of - created).days > TRIAGE_DAYS:
        reason = _pick(rng, {"sem_perfil": 40, "sem_contato": 35, "fora_de_icp": 25})
        return "disqualified", reason
    return "open", None


def _simulate_cycle(
    rng: random.Random,
    as_of: date,
    opened_at: date,
    will_win: bool,
) -> dict[str, object] | None:
    """Monta o histórico de etapas visível até a data de corte."""
    qual_days = rng.randint(8, 28)
    proposal_days = rng.randint(12, 40)
    negotiation_days = rng.randint(14, 50)
    proposal_at = opened_at + timedelta(days=qual_days)
    negotiation_at = proposal_at + timedelta(days=proposal_days)
    decision_at = negotiation_at + timedelta(days=negotiation_days)
    loss_stage = _pick(rng, {"qualificacao": 30, "proposta": 42, "negociacao": 28})

    if will_win:
        boundaries = [
            ("qualificacao", opened_at, proposal_at),
            ("proposta", proposal_at, negotiation_at),
            ("negociacao", negotiation_at, decision_at),
            ("ganho", decision_at, decision_at),
        ]
        planned_close = decision_at
        closed_stage = "ganho"
    elif loss_stage == "qualificacao":
        planned_close = proposal_at
        boundaries = [("qualificacao", opened_at, planned_close)]
        closed_stage = "qualificacao"
    elif loss_stage == "proposta":
        planned_close = negotiation_at
        boundaries = [
            ("qualificacao", opened_at, proposal_at),
            ("proposta", proposal_at, planned_close),
        ]
        closed_stage = "proposta"
    else:
        planned_close = decision_at
        boundaries = [
            ("qualificacao", opened_at, proposal_at),
            ("proposta", proposal_at, negotiation_at),
            ("negociacao", negotiation_at, planned_close),
        ]
        closed_stage = "negociacao"

    if opened_at > as_of:
        return None

    history: list[tuple[str, date, date | None]] = []
    current = "qualificacao"
    for stage, entered, exited in boundaries:
        if entered > as_of:
            break
        if exited <= as_of:
            history.append((stage, entered, exited))
            current = stage
        else:
            history.append((stage, entered, None))
            current = stage
            break

    if planned_close <= as_of:
        status = "won" if will_win else "lost"
        stage = closed_stage
        closed_at: date | None = planned_close
        probability = 1.0 if will_win else 0.0
        expected_close = planned_close
        loss_reason = (
            None
            if will_win
            else _pick(
                rng,
                {
                    "preco": 28,
                    "concorrente": 18,
                    "sem_budget": 16,
                    "sem_fit": 14,
                    "sem_resposta": 14,
                    "timing": 10,
                },
            )
        )
    else:
        status = "open"
        stage = current
        closed_at = None
        probability = STAGE_PROBABILITY[current]
        expected_close = planned_close
        loss_reason = None

    return {
        "stage": stage,
        "status": status,
        "closed_at": closed_at,
        "expected_close_date": expected_close,
        "probability": probability,
        "loss_reason": loss_reason,
        "history": history,
    }


def _churn_probability(
    rng_month: date,
    porte: str,
    channel: str,
    sector: str,
    frailty: float,
) -> float:
    probability = 0.0205 * PORTE_RISK[porte] * CHANNEL_RISK[channel] * SECTOR_RISK[sector] * frailty
    if rng_month.month == 1:
        probability *= 1.34
    elif rng_month.month == 12:
        probability *= 0.80
    return min(probability, 0.12)


def _churn_reason(rng: random.Random, porte: str, frailty: float) -> str:
    if porte == "mei":
        weights = {
            "encerrou_atividade": 26,
            "preco": 24,
            "baixo_uso": 18,
            "produto": 12,
            "suporte": 10,
            "concorrente": 10,
        }
    elif frailty >= 1.25:
        weights = {
            "suporte": 22,
            "produto": 16,
            "preco": 18,
            "baixo_uso": 16,
            "concorrente": 16,
            "encerrou_atividade": 12,
        }
    else:
        weights = {
            "preco": 22,
            "baixo_uso": 20,
            "concorrente": 18,
            "produto": 16,
            "suporte": 14,
            "encerrou_atividade": 10,
        }
    return _pick(rng, weights)


def _ticket_count(rng: random.Random, frailty: float) -> int:
    probability = min(0.7, 0.16 + 0.18 * frailty)
    count = 0
    while count < 5 and rng.random() < probability:
        count += 1
        probability *= 0.55
    return count


def _build_campaigns(rng: random.Random, months: list[date]) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    serial = 1
    for month in months:
        for channel in CHANNELS:
            base = EVENT_SPEND if channel == "event" and month.month in EVENT_MONTHS else CHANNEL_SPEND[channel]
            spend = 0.0 if base == 0 else round(base * rng.uniform(0.90, 1.10), 2)
            rows.append(
                {
                    "campaign_id": f"K{serial:04d}",
                    "campaign_name": f"{CHANNEL[channel]} {month:%Y-%m}",
                    "channel": channel,
                    "month_start": month,
                    "spend_brl": spend,
                }
            )
            serial += 1
    return rows


def _price(rng: random.Random, porte: str) -> tuple[str, int, int]:
    plan = _pick(rng, PLAN_WEIGHTS[porte])
    mrr_cents = int(PLAN_MRR[(porte, plan)] * 100)
    setup_cents = mrr_cents * rng.choice([0, 0, 1, 1, 2])
    return plan, mrr_cents, setup_cents


def _invoice(
    rng: random.Random,
    as_of: date,
    last_month: date,
    month: date,
    amount_cents: int,
    frailty: float,
    invoice_type: str,
) -> dict[str, object]:
    issued = min(month + timedelta(days=2), as_of)
    due = issued + timedelta(days=10)
    late = rng.random() < min(0.58, 0.045 + 0.11 * max(frailty - 0.4, 0))
    if late:
        paid = due + timedelta(days=rng.randint(4, 27))
    else:
        paid = issued + timedelta(days=rng.randint(0, 8))

    if month < last_month:
        status = "paid"
        paid_at: date | None = min(paid, as_of)
    elif paid <= as_of and rng.random() > 0.22:
        status = "paid"
        paid_at = paid
    elif due < as_of:
        status = "overdue"
        paid_at = None
    else:
        status = "open"
        paid_at = None
    return {
        "month_start": month,
        "invoice_type": invoice_type,
        "amount_brl": _money(amount_cents),
        "status": status,
        "issued_at": issued,
        "due_at": due,
        "paid_at": paid_at,
    }


def _simulate_subscription(
    rng: random.Random,
    as_of: date,
    months: list[date],
    start_on: date,
    mrr_cents: int,
    setup_cents: int,
    porte: str,
    channel: str,
    sector: str,
) -> dict[str, object]:
    start_month = date(start_on.year, start_on.month, 1)
    last_month = date(as_of.year, as_of.month, 1)
    frailty = rng.uniform(0.62, 1.48)
    movements: list[dict[str, object]] = []
    invoices: list[dict[str, object]] = []
    active_months: list[date] = []
    current = mrr_cents
    end_date: date | None = None
    churn_meta: dict[str, object] | None = None
    seen = 0

    for month in months:
        if month < start_month:
            continue
        if month == start_month:
            movements.append(
                {
                    "month_start": month,
                    "beginning_mrr": 0.0,
                    "new_mrr": _money(current),
                    "expansion_mrr": 0.0,
                    "contraction_mrr": 0.0,
                    "churn_mrr": 0.0,
                    "ending_mrr": _money(current),
                }
            )
            if setup_cents:
                invoices.append(_invoice(rng, as_of, last_month, month, setup_cents, frailty, "setup"))
            invoices.append(_invoice(rng, as_of, last_month, month, current, frailty, "subscription"))
            active_months.append(month)
            seen = 1
            continue

        probability = _churn_probability(month, porte, channel, sector, frailty)
        if rng.random() < probability:
            movements.append(
                {
                    "month_start": month,
                    "beginning_mrr": _money(current),
                    "new_mrr": 0.0,
                    "expansion_mrr": 0.0,
                    "contraction_mrr": 0.0,
                    "churn_mrr": _money(current),
                    "ending_mrr": 0.0,
                }
            )
            end_date = month
            churn_meta = {
                "churn_date": month,
                "reason": _churn_reason(rng, porte, frailty),
                "mrr_lost": _money(current),
                "tenure_months": seen,
            }
            break

        expansion = 0
        contraction = 0
        if seen >= 4 and rng.random() < (0.05 if frailty < 1 else 0.028):
            grown = int(round(current * (1 + rng.choice([0.12, 0.18, 0.25, 0.32]))))
            expansion = grown - current
            current = grown
        elif seen >= 3 and rng.random() < 0.012 * frailty:
            reduced = max(int(round(current * (1 - rng.choice([0.10, 0.15, 0.22])))), 9900)
            contraction = current - reduced
            current = reduced

        movements.append(
            {
                "month_start": month,
                "beginning_mrr": _money(current - expansion + contraction),
                "new_mrr": 0.0,
                "expansion_mrr": _money(expansion),
                "contraction_mrr": _money(contraction),
                "churn_mrr": 0.0,
                "ending_mrr": _money(current),
            }
        )
        invoices.append(_invoice(rng, as_of, last_month, month, current, frailty, "subscription"))
        active_months.append(month)
        seen += 1

    # Parte de quem cancela abre mais chamado e atrasa fatura nos dois
    # meses ativos anteriores. Quem fica também reclama às vezes, e parte
    # de quem sai não avisa. O rastro existe, mas não é determinístico.
    signal_months: set[date] = set()
    if end_date is not None and rng.random() < 0.72:
        signal_months = {_add_months(end_date, -1), _add_months(end_date, -2)}
    elif end_date is None and active_months and rng.random() < 0.14:
        signal_months = {rng.choice(active_months)}

    for invoice in invoices:
        if invoice["month_start"] not in signal_months or invoice["invoice_type"] != "subscription":
            continue
        if invoice["status"] != "paid" or invoice["paid_at"] is None:
            continue
        paid_at = invoice["paid_at"] + timedelta(days=rng.randint(12, 24))
        if paid_at <= as_of:
            invoice["paid_at"] = paid_at
            invoice["status"] = "paid"
        else:
            invoice["paid_at"] = None
            invoice["status"] = "overdue"

    tickets: list[dict[str, object]] = []
    for month in active_months:
        ticket_total = _ticket_count(rng, frailty)
        if month in signal_months:
            ticket_total += rng.randint(2, 4)
        stressed = month in signal_months
        for _ in range(ticket_total):
            opened = month + timedelta(days=rng.randrange(_month_end_span(month)))
            if opened > as_of:
                opened = as_of
            priority = _pick(
                rng,
                {"baixa": 18, "media": 28, "alta": 34, "urgente": 20}
                if stressed
                else {"baixa": 48, "media": 32, "alta": 15, "urgente": 5},
            )
            category = _pick(
                rng,
                {
                    "duvida": 30,
                    "cobranca": 18,
                    "bug": 16,
                    "implantacao": 14,
                    "treinamento": 12,
                    "indisponibilidade": 10,
                },
            )
            hours = round(
                rng.uniform(1.5, 36) * {"baixa": 0.7, "media": 1, "alta": 1.3, "urgente": 1.6}[priority],
                1,
            )
            close_on = opened + timedelta(days=max(0, int(round(hours / 8))))
            recent = (as_of - opened).days <= 12 and rng.random() < 0.45
            if recent or close_on > as_of:
                status = "open"
                closed_at = None
                csat = None
            else:
                status = "closed"
                closed_at = close_on
                center = 2.6 if stressed else 4.5 - 0.35 * min(frailty, 2.0)
                csat = max(1, min(5, int(round(rng.gauss(center, 0.55)))))
            tickets.append(
                {
                    "opened_at": opened,
                    "closed_at": closed_at,
                    "priority": priority,
                    "category": category,
                    "status": status,
                    "csat": csat,
                    "resolution_hours": None if status == "open" else hours,
                }
            )

    return {
        "movements": movements,
        "invoices": invoices,
        "tickets": tickets,
        "end_date": end_date,
        "current_mrr": 0 if end_date else _money(current),
        "churn": churn_meta,
        "status": "churned" if end_date else "active",
    }


def _records_to_frames(bundle: dict[str, list[dict[str, object]]]) -> dict[str, pd.DataFrame]:
    return {name: _frame(rows) for name, rows in bundle.items()}


def generate(
    seed: int = 42,
    start: date = START_DEFAULT,
    end: date = AS_OF_DEFAULT,
    output_dir: Path | None = None,
    monthly_leads: int = 148,
    write: bool = True,
) -> dict[str, pd.DataFrame]:
    """Gera as tabelas operacionais e, se `write`, grava CSV e DuckDB."""
    rng = random.Random(seed)
    as_of = end
    months = _month_starts(start, end)
    campaigns = _build_campaigns(rng, months)
    campaign_index = {(row["channel"], row["month_start"]): row["campaign_id"] for row in campaigns}

    companies: list[dict[str, object]] = []
    contacts: list[dict[str, object]] = []
    leads: list[dict[str, object]] = []
    opportunities: list[dict[str, object]] = []
    stages: list[dict[str, object]] = []
    subscriptions: list[dict[str, object]] = []
    movements: list[dict[str, object]] = []
    invoices: list[dict[str, object]] = []
    churn_events: list[dict[str, object]] = []
    tickets: list[dict[str, object]] = []

    company_serial = 1
    contact_serial = 1
    lead_serial = 1
    opp_serial = 1
    sub_serial = 1
    invoice_serial = 1
    churn_serial = 1
    ticket_serial = 1

    for month in months:
        volume = max(24, int(round(monthly_leads * MONTH_SEASON[month.month] * rng.uniform(0.94, 1.06))))
        for _ in range(volume):
            porte = _pick(rng, PORTE_WEIGHTS)
            sector = _pick(rng, SECTOR_WEIGHTS)
            state = _pick(rng, UF_WEIGHTS)
            channel = _pick(rng, CHANNEL_WEIGHTS)
            created = _random_day(rng, month)
            lo, hi = EMPLOYEE_RANGE[porte]
            employees = lo if lo == hi else rng.randint(lo, hi)
            revenue_lo, revenue_hi = REVENUE_RANGE[porte]
            company_id = f"C{company_serial:05d}"
            company_serial += 1
            companies.append(
                {
                    "company_id": company_id,
                    "company_name": (f"{rng.choice(NAME_PREFIXES)} {rng.choice(NAME_CORES)} {company_serial:04d}"),
                    "porte": porte,
                    "sector": sector,
                    "state_uf": state,
                    "city": rng.choice(CITIES[state]),
                    "employees": employees,
                    "annual_revenue_brl": round(rng.uniform(revenue_lo, revenue_hi), 2),
                    "created_at": created,
                }
            )

            primary_name = f"{rng.choice(FIRST_NAMES)} {rng.choice(LAST_NAMES)}"
            primary_id = f"P{contact_serial:05d}"
            contact_serial += 1
            contacts.append(
                {
                    "contact_id": primary_id,
                    "company_id": company_id,
                    "full_name": primary_name,
                    "role": _pick(rng, {"decision_maker": 70, "champion": 30}),
                    "email": f"{_slug(primary_name)}.{contact_serial}@exemplo-ficticio.test",
                    "phone": f"+55 00 9{rng.randrange(1000, 9999)}-{rng.randrange(1000, 9999)}",
                    "is_primary": True,
                }
            )
            extra_contacts = 2 if rng.random() < 0.12 else 1 if rng.random() < 0.38 else 0
            for _extra in range(extra_contacts):
                extra_name = f"{rng.choice(FIRST_NAMES)} {rng.choice(LAST_NAMES)}"
                contacts.append(
                    {
                        "contact_id": f"P{contact_serial:05d}",
                        "company_id": company_id,
                        "full_name": extra_name,
                        "role": _pick(rng, {"user": 45, "finance": 30, "champion": 25}),
                        "email": f"{_slug(extra_name)}.{contact_serial}@exemplo-ficticio.test",
                        "phone": f"+55 00 9{rng.randrange(1000, 9999)}-{rng.randrange(1000, 9999)}",
                        "is_primary": False,
                    }
                )
                contact_serial += 1

            p_mql, p_sql, p_opp, p_win = CHANNEL_CONVERSION[channel]
            mql_at = created + timedelta(days=rng.randint(0, 16)) if rng.random() < p_mql else None
            sql_at = None
            if mql_at is not None and rng.random() < p_sql:
                sql_at = mql_at + timedelta(days=rng.randint(2, 24))
            opp_at = None
            if sql_at is not None and rng.random() < p_opp:
                opp_at = sql_at + timedelta(days=rng.randint(0, 8))

            observed_mql = mql_at if mql_at is not None and mql_at <= as_of else None
            observed_sql = sql_at if sql_at is not None and sql_at <= as_of else None
            cycle = None
            if opp_at is not None and observed_sql is not None:
                will_win = rng.random() < min(0.82, p_win * PORTE_WIN[porte])
                cycle = _simulate_cycle(rng, as_of, opp_at, will_win)

            opp_status = None if cycle is None else str(cycle["status"])
            status, reason = _lead_status(created, observed_mql, observed_sql, opp_status, as_of, rng)
            lead_id = f"L{lead_serial:05d}"
            lead_serial += 1
            leads.append(
                {
                    "lead_id": lead_id,
                    "company_id": company_id,
                    "contact_id": primary_id,
                    "campaign_id": campaign_index[(channel, month)],
                    "channel": channel,
                    "created_at": created,
                    "mql_at": observed_mql,
                    "sql_at": observed_sql,
                    "status": status,
                    "disqualified_reason": reason,
                }
            )

            if cycle is None:
                continue

            plan, mrr_cents, setup_cents = _price(rng, porte)
            opportunity_id = f"O{opp_serial:05d}"
            opp_serial += 1
            opportunities.append(
                {
                    "opportunity_id": opportunity_id,
                    "lead_id": lead_id,
                    "company_id": company_id,
                    "campaign_id": campaign_index[(channel, month)],
                    "channel": channel,
                    "owner_name": rng.choice(OWNERS),
                    "plan": plan,
                    "stage": cycle["stage"],
                    "status": cycle["status"],
                    "created_at": opp_at,
                    "expected_close_date": cycle["expected_close_date"],
                    "closed_at": cycle["closed_at"],
                    "mrr_brl": _money(mrr_cents),
                    "setup_fee_brl": _money(setup_cents),
                    "acv_brl": _money(mrr_cents * 12 + setup_cents),
                    "probability": cycle["probability"],
                    "loss_reason": cycle["loss_reason"],
                }
            )
            for order, (stage, entered, exited) in enumerate(cycle["history"], start=1):
                stages.append(
                    {
                        "opportunity_id": opportunity_id,
                        "stage": stage,
                        "stage_order": order,
                        "entered_at": entered,
                        "exited_at": exited,
                    }
                )

            if cycle["status"] != "won":
                continue

            life = _simulate_subscription(
                rng,
                as_of,
                months,
                cycle["closed_at"],
                mrr_cents,
                setup_cents,
                porte,
                channel,
                sector,
            )
            subscription_id = f"S{sub_serial:05d}"
            sub_serial += 1
            subscriptions.append(
                {
                    "subscription_id": subscription_id,
                    "company_id": company_id,
                    "opportunity_id": opportunity_id,
                    "plan": plan,
                    "channel": channel,
                    "start_date": cycle["closed_at"],
                    "end_date": life["end_date"],
                    "initial_mrr_brl": _money(mrr_cents),
                    "current_mrr_brl": life["current_mrr"],
                    "status": life["status"],
                }
            )
            for movement in life["movements"]:
                movements.append({"company_id": company_id, **movement})
            for invoice in life["invoices"]:
                invoices.append(
                    {
                        "invoice_id": f"I{invoice_serial:06d}",
                        "company_id": company_id,
                        "subscription_id": subscription_id,
                        **invoice,
                    }
                )
                invoice_serial += 1
            if life["churn"] is not None:
                churn_events.append(
                    {
                        "churn_id": f"H{churn_serial:05d}",
                        "company_id": company_id,
                        "subscription_id": subscription_id,
                        **life["churn"],
                    }
                )
                churn_serial += 1
            for ticket in life["tickets"]:
                tickets.append(
                    {
                        "ticket_id": f"T{ticket_serial:06d}",
                        "company_id": company_id,
                        **ticket,
                    }
                )
                ticket_serial += 1

    params = [
        {
            "as_of_date": as_of,
            "period_start": start,
            "period_end": end,
            "gross_margin": GROSS_MARGIN,
            "seed": seed,
            "currency": "BRL",
            "vendor_name": VENDOR_NAME,
            "product_name": PRODUCT_NAME,
        }
    ]
    bundle = {
        "params": params,
        "companies": companies,
        "contacts": contacts,
        "campaigns": campaigns,
        "leads": leads,
        "opportunities": opportunities,
        "opportunity_stages": stages,
        "subscriptions": subscriptions,
        "mrr_movements": movements,
        "invoices": invoices,
        "churn_events": churn_events,
        "support_tickets": tickets,
    }
    frames = _records_to_frames(bundle)
    if write:
        target = output_dir or (ROOT / "data")
        _write_outputs(target, frames, seed, start, end)
    return frames


def _write_outputs(
    output_dir: Path,
    frames: dict[str, pd.DataFrame],
    seed: int,
    start: date,
    end: date,
) -> None:
    raw = output_dir / "raw"
    warehouse = output_dir / "warehouse"
    star_dir = warehouse / "star"
    raw.mkdir(parents=True, exist_ok=True)
    star_dir.mkdir(parents=True, exist_ok=True)

    for name, frame in frames.items():
        frame.to_csv(raw / f"{name}.csv", index=False)

    star = _star_schema(frames, end)
    for name, frame in star.items():
        frame.to_csv(star_dir / f"{name}.csv", index=False)

    db_path = warehouse / "crm.duckdb"
    if db_path.exists():
        db_path.unlink()
    connection = duckdb.connect(str(db_path))
    try:
        connection.execute((ROOT / "sql" / "schema.sql").read_text(encoding="utf-8"))
        for name, frame in frames.items():
            connection.register(f"src_{name}", frame)
            connection.execute(f"INSERT INTO {name} BY NAME SELECT * FROM src_{name}")
        for name, frame in star.items():
            connection.register(f"src_{name}", frame)
            connection.execute(f"CREATE TABLE {name} AS SELECT * FROM src_{name}")
    finally:
        connection.close()

    summary = {
        "seed": seed,
        "period_start": start.isoformat(),
        "period_end": end.isoformat(),
        "vendor_name": VENDOR_NAME,
        "note": "Base 100% fictícia gerada por data/generate.py.",
        "rows": {name: int(len(frame)) for name, frame in frames.items()},
    }
    (warehouse / "summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def _star_schema(frames: dict[str, pd.DataFrame], as_of: date) -> dict[str, pd.DataFrame]:
    companies = frames["companies"]
    subscriptions = frames["subscriptions"]
    leads = frames["leads"]
    opportunities = frames["opportunities"]
    movements = frames["mrr_movements"]
    invoices = frames["invoices"]
    tickets = frames["support_tickets"]
    churn = frames["churn_events"]
    campaigns = frames["campaigns"]

    sub_by_company = subscriptions.set_index("company_id")
    dim_company_rows: list[dict[str, object]] = []
    for company in companies.itertuples(index=False):
        if company.company_id in sub_by_company.index:
            sub = sub_by_company.loc[company.company_id]
            status = sub.status
            plan = sub.plan
            channel = sub.channel
            cohort = date(sub.start_date.year, sub.start_date.month, 1)
            current_mrr = sub.current_mrr_brl
        else:
            status = "prospect"
            plan = None
            channel = None
            cohort = None
            current_mrr = 0.0
        dim_company_rows.append(
            {
                "company_id": company.company_id,
                "company_name": company.company_name,
                "porte_code": company.porte,
                "porte_name": PORTE[company.porte],
                "sector_code": company.sector,
                "sector_name": SECTOR[company.sector],
                "state_uf": company.state_uf,
                "state_name": UF_NAME[company.state_uf],
                "city": company.city,
                "employees": company.employees,
                "annual_revenue_brl": company.annual_revenue_brl,
                "created_at": company.created_at,
                "status": status,
                "plan_code": plan,
                "plan_name": None if plan is None else PLAN[plan],
                "acquisition_channel_code": channel,
                "acquisition_channel_name": None if channel is None else CHANNEL[channel],
                "cohort_month": cohort,
                "current_mrr_brl": current_mrr,
            }
        )

    start_dim = date(2023, 1, 1)
    end_dim = as_of + timedelta(days=400)
    dim_dates = []
    cursor = start_dim
    while cursor <= end_dim:
        dim_dates.append(
            {
                "date_key": _date_key(cursor),
                "full_date": cursor,
                "month_start": date(cursor.year, cursor.month, 1),
                "year": cursor.year,
                "quarter": (cursor.month - 1) // 3 + 1,
                "month": cursor.month,
                "year_month": f"{cursor:%Y-%m}",
            }
        )
        cursor += timedelta(days=1)

    won_leads = set(opportunities.loc[opportunities["status"] == "won", "lead_id"])
    lost_leads = set(opportunities.loc[opportunities["status"] == "lost", "lead_id"])
    open_leads = set(opportunities.loc[opportunities["status"] == "open", "lead_id"])
    opp_leads = set(opportunities["lead_id"])
    company_porte = companies.set_index("company_id")["porte"]
    company_sector = companies.set_index("company_id")["sector"]

    fact_lead = []
    for lead in leads.itertuples(index=False):
        fact_lead.append(
            {
                "lead_id": lead.lead_id,
                "company_id": lead.company_id,
                "date_key": _date_key(lead.created_at),
                "channel_code": lead.channel,
                "porte_code": company_porte.loc[lead.company_id],
                "sector_code": company_sector.loc[lead.company_id],
                "campaign_id": lead.campaign_id,
                "is_mql": lead.mql_at is not None and not pd.isna(lead.mql_at),
                "is_sql": lead.sql_at is not None and not pd.isna(lead.sql_at),
                "is_opportunity": lead.lead_id in opp_leads,
                "is_won": lead.lead_id in won_leads,
                "is_lost": lead.lead_id in lost_leads,
                "is_open_opportunity": lead.lead_id in open_leads,
            }
        )

    plan_by_company = subscriptions.set_index("company_id")["plan"] if len(subscriptions) else pd.Series(dtype=object)
    channel_by_company = (
        subscriptions.set_index("company_id")["channel"] if len(subscriptions) else pd.Series(dtype=object)
    )
    fact_mrr = []
    for movement in movements.itertuples(index=False):
        fact_mrr.append(
            {
                "company_id": movement.company_id,
                "date_key": _date_key(movement.month_start),
                "month_start": movement.month_start,
                "porte_code": company_porte.loc[movement.company_id],
                "channel_code": channel_by_company.loc[movement.company_id],
                "plan_code": plan_by_company.loc[movement.company_id],
                "beginning_mrr": movement.beginning_mrr,
                "new_mrr": movement.new_mrr,
                "expansion_mrr": movement.expansion_mrr,
                "contraction_mrr": movement.contraction_mrr,
                "churn_mrr": movement.churn_mrr,
                "ending_mrr": movement.ending_mrr,
            }
        )

    fact_opportunity = []
    for opp in opportunities.itertuples(index=False):
        cycle_days = None
        if opp.closed_at is not None and not pd.isna(opp.closed_at):
            cycle_days = (opp.closed_at - opp.created_at).days
        fact_opportunity.append(
            {
                "opportunity_id": opp.opportunity_id,
                "lead_id": opp.lead_id,
                "company_id": opp.company_id,
                "date_key": _date_key(opp.created_at),
                "close_date_key": _date_key(None if pd.isna(opp.closed_at) else opp.closed_at),
                "expected_close_date_key": _date_key(opp.expected_close_date),
                "channel_code": opp.channel,
                "porte_code": company_porte.loc[opp.company_id],
                "plan_code": opp.plan,
                "stage_code": opp.stage,
                "status": opp.status,
                "mrr_brl": opp.mrr_brl,
                "acv_brl": opp.acv_brl,
                "probability": opp.probability,
                "weighted_acv": round(opp.acv_brl * opp.probability, 2),
                "cycle_days": cycle_days,
                "loss_reason_code": None if pd.isna(opp.loss_reason) else opp.loss_reason,
            }
        )

    fact_invoice = []
    for invoice in invoices.itertuples(index=False):
        days_late = None
        if invoice.paid_at is not None and not pd.isna(invoice.paid_at):
            days_late = max(0, (invoice.paid_at - invoice.due_at).days)
        fact_invoice.append(
            {
                "invoice_id": invoice.invoice_id,
                "company_id": invoice.company_id,
                "date_key": _date_key(invoice.issued_at),
                "month_start": invoice.month_start,
                "invoice_type": invoice.invoice_type,
                "amount_brl": invoice.amount_brl,
                "status": invoice.status,
                "days_late": days_late,
            }
        )

    fact_ticket = []
    for ticket in tickets.itertuples(index=False):
        fact_ticket.append(
            {
                "ticket_id": ticket.ticket_id,
                "company_id": ticket.company_id,
                "opened_date_key": _date_key(ticket.opened_at),
                "porte_code": company_porte.loc[ticket.company_id],
                "priority": ticket.priority,
                "category": ticket.category,
                "status": ticket.status,
                "csat": None if pd.isna(ticket.csat) else int(ticket.csat),
                "resolution_hours": None if pd.isna(ticket.resolution_hours) else ticket.resolution_hours,
            }
        )

    fact_churn = []
    for event in churn.itertuples(index=False):
        fact_churn.append(
            {
                "churn_id": event.churn_id,
                "company_id": event.company_id,
                "date_key": _date_key(event.churn_date),
                "reason_code": event.reason,
                "reason_name": CHURN_REASON[event.reason],
                "mrr_lost": event.mrr_lost,
                "tenure_months": event.tenure_months,
                "porte_code": company_porte.loc[event.company_id],
                "channel_code": channel_by_company.loc[event.company_id],
            }
        )

    def _dim(rows: list[tuple[str, str]], code_name: str, label_name: str) -> pd.DataFrame:
        return pd.DataFrame([{code_name: code, label_name: label} for code, label in rows])

    star = {
        "dim_date": pd.DataFrame(dim_dates),
        "dim_company": pd.DataFrame(dim_company_rows),
        "dim_channel": _dim(list(CHANNEL.items()), "channel_code", "channel_name"),
        "dim_porte": _dim(list(PORTE.items()), "porte_code", "porte_name"),
        "dim_sector": _dim(list(SECTOR.items()), "sector_code", "sector_name"),
        "dim_plan": _dim(list(PLAN.items()), "plan_code", "plan_name"),
        "dim_stage": _dim(list(STAGE.items()), "stage_code", "stage_name"),
        "dim_churn_reason": _dim(list(CHURN_REASON.items()), "reason_code", "reason_name"),
        "dim_loss_reason": _dim(list(LOSS_REASON.items()), "loss_reason_code", "loss_reason_name"),
        "dim_campaign": campaigns.rename(columns={"channel": "channel_code"})[
            ["campaign_id", "campaign_name", "channel_code", "month_start", "spend_brl"]
        ],
        "fact_lead": pd.DataFrame(fact_lead),
        "fact_opportunity": pd.DataFrame(fact_opportunity),
        "fact_mrr_month": pd.DataFrame(fact_mrr),
        "fact_invoice": pd.DataFrame(fact_invoice),
        "fact_ticket": pd.DataFrame(fact_ticket),
        "fact_churn": pd.DataFrame(fact_churn),
    }
    return star


def main() -> None:
    parser = argparse.ArgumentParser(description="Gera a base fictícia de CRM da Nexora.")
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--output", type=Path, default=ROOT / "data")
    args = parser.parse_args()
    frames = generate(seed=args.seed, output_dir=args.output)
    print("Base fictícia gravada em", args.output)
    for name, frame in frames.items():
        print(f"  {name}: {len(frame)}")


if __name__ == "__main__":
    main()

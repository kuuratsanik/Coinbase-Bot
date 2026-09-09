"""Parse a plain-English trading instruction into a structured, reviewable plan.

The default parser is fully deterministic and offline (regex + a ticker lexicon),
so "ask AI to do it" works with zero credentials and is safe to unit-test. If an
LLM is configured (``CBDCA_LLM=1`` and the ``openai`` package + ``OPENAI_API_KEY``
present), :func:`parse` can delegate to it, but the deterministic path remains the
guaranteed baseline.

A plan is always presented for review; execution is explicit and defaults to the
offline paper venue, so an ambiguous request can never move real funds by
surprise.
"""

from __future__ import annotations

import os
import re
from dataclasses import dataclass, field

from src.trading import catalog
from src.trading.models import Order, OrderResult, OrderSide

# A pragmatic lexicon of common crypto tickers for symbol extraction.
KNOWN_TICKERS = {
    "BTC",
    "ETH",
    "SOL",
    "ADA",
    "XRP",
    "DOGE",
    "LINK",
    "LTC",
    "BCH",
    "DOT",
    "MATIC",
    "AVAX",
    "UNI",
    "ATOM",
    "XLM",
    "ALGO",
    "FIL",
    "ICP",
    "APT",
    "ARB",
    "OP",
    "SUI",
    "SHIB",
    "TRX",
    "NEAR",
    "AAVE",
    "MKR",
    "SAND",
    "MANA",
    "GRT",
    "USDC",
    "USDT",
}

_FREQUENCIES = {
    "hourly": "hourly",
    "daily": "daily",
    "day": "daily",
    "weekly": "weekly",
    "week": "weekly",
    "biweekly": "biweekly",
    "fortnight": "biweekly",
    "monthly": "monthly",
    "month": "monthly",
    "payday": "monthly",
}

_DEFAULT_AMOUNT = 100.0


@dataclass
class PlanLeg:
    symbol: str
    quote_amount: float
    assumed_amount: bool = False


@dataclass
class Plan:
    raw_text: str
    provider_id: str = "paper"
    adapter: str = "paper"
    side: OrderSide = OrderSide.BUY
    legs: list[PlanLeg] = field(default_factory=list)
    frequency: str | None = None
    quote_currency: str = "USD"
    warnings: list[str] = field(default_factory=list)

    @property
    def is_actionable(self) -> bool:
        return bool(self.legs)

    @property
    def total_amount(self) -> float:
        return round(sum(leg.quote_amount for leg in self.legs), 2)


def _resolve_provider(text: str) -> tuple[str, str, list[str]]:
    """Return (provider_id, adapter, warnings) by matching catalog names/ids."""

    warnings: list[str] = []
    lowered = text.lower()
    id_matches: list[catalog.Service] = []
    name_matches: list[catalog.Service] = []
    for svc in catalog.all_services():
        if svc.category.value in {"notifier", "scheduler", "secrets", "market_data"}:
            continue
        if re.search(rf"\b{re.escape(svc.id.lower())}\b", lowered):
            id_matches.append(svc)
            continue
        name_needle = svc.name.lower().split(" ")[0]
        if len(name_needle) >= 4 and re.search(rf"\b{re.escape(name_needle)}\b", lowered):
            name_matches.append(svc)
    # An exact id match is the most specific; fall back to a name match.
    candidates = id_matches or name_matches
    best: catalog.Service | None = None
    if candidates:
        best = min(candidates, key=lambda s: len(s.id))
    if best is None:
        return "paper", "paper", warnings
    if best.adapter is None:
        warnings.append(
            f"'{best.name}' is in the catalog but has no bundled adapter yet; falling back to the paper simulator."
        )
        return best.id, "paper", warnings
    return best.id, best.adapter, warnings


def _extract_frequency(text: str) -> str | None:
    lowered = text.lower()
    if "every" in lowered or "recurring" in lowered or "dca" in lowered:
        for word, freq in _FREQUENCIES.items():
            if word in lowered:
                return freq
        return "weekly"
    for word, freq in _FREQUENCIES.items():
        if re.search(rf"\b{word}\b", lowered):
            return freq
    return None


def _extract_legs(text: str) -> tuple[list[PlanLeg], list[str]]:
    warnings: list[str] = []

    tickers: list[str] = []
    for token in re.findall(r"[A-Za-z]{2,6}", text):
        t = token.upper()
        if t in KNOWN_TICKERS and t not in tickers:
            tickers.append(t)
    if not tickers:
        return [], warnings

    # Explicit "amount of/in/into TICKER" pairs (e.g. "$50 of BTC").
    pair_re = re.compile(
        r"\$?\s*(\d+(?:\.\d+)?)\s*(?:usd|dollars?|\$|bucks)?\s*(?:worth\s*)?(?:of|in|into)\s+([a-zA-Z]{2,6})",
        re.IGNORECASE,
    )
    pairs: dict[str, float] = {}
    for amount, ticker in pair_re.findall(text):
        t = ticker.upper()
        if t in KNOWN_TICKERS:
            pairs[t] = float(amount)

    # All standalone amounts, in text order.
    amounts = [float(m) for m in re.findall(r"\$\s*(\d+(?:\.\d+)?)", text)]
    if not amounts:
        amounts = [float(m) for m in re.findall(r"(\d+(?:\.\d+)?)\s*(?:usd|dollars?|bucks)", text, re.IGNORECASE)]
    distinct = set(amounts)

    legs: list[PlanLeg] = []
    if pairs and len(pairs) == len(tickers):
        legs = [PlanLeg(symbol=f"{t}-USD", quote_amount=pairs[t]) for t in tickers]
    elif len(distinct) == 1:
        # "$50 of BTC and ETH" / "buy $50 BTC ETH SOL" -> same amount for each.
        amt = next(iter(distinct))
        legs = [PlanLeg(symbol=f"{t}-USD", quote_amount=amt) for t in tickers]
    elif amounts and len(amounts) == len(tickers):
        # "$50 BTC and $100 ETH" -> pair positionally.
        legs = [PlanLeg(symbol=f"{t}-USD", quote_amount=a) for t, a in zip(tickers, amounts, strict=True)]
    elif pairs:
        for t in tickers:
            if t in pairs:
                legs.append(PlanLeg(symbol=f"{t}-USD", quote_amount=pairs[t]))
            else:
                warnings.append(f"No amount for {t}; assuming ${_DEFAULT_AMOUNT:.0f}.")
                legs.append(PlanLeg(symbol=f"{t}-USD", quote_amount=_DEFAULT_AMOUNT, assumed_amount=True))
    else:
        warnings.append(f"No amount detected; assuming ${_DEFAULT_AMOUNT:.0f} per asset.")
        legs = [PlanLeg(symbol=f"{t}-USD", quote_amount=_DEFAULT_AMOUNT, assumed_amount=True) for t in tickers]
    return legs, warnings


def parse(text: str) -> Plan:
    """Parse ``text`` into a :class:`Plan` (deterministic; optional LLM assist)."""

    if _llm_enabled():
        llm_plan = _parse_with_llm(text)
        if llm_plan is not None:
            return llm_plan

    side = OrderSide.SELL if re.search(r"\bsell\b", text, re.IGNORECASE) else OrderSide.BUY
    provider_id, adapter, provider_warnings = _resolve_provider(text)
    legs, leg_warnings = _extract_legs(text)
    plan = Plan(
        raw_text=text,
        provider_id=provider_id,
        adapter=adapter,
        side=side,
        legs=legs,
        frequency=_extract_frequency(text),
        warnings=provider_warnings + leg_warnings,
    )
    if not plan.is_actionable:
        plan.warnings.append("Could not identify any tradable asset. Mention a ticker like BTC or ETH.")
    return plan


def format_plan(plan: Plan) -> str:
    lines = [
        f"Request : {plan.raw_text}",
        f"Provider: {plan.provider_id} (adapter: {plan.adapter})",
        f"Action  : {plan.side.value.upper()}" + (f", recurring {plan.frequency}" if plan.frequency else ", one-time"),
    ]
    if plan.legs:
        lines.append("Orders  :")
        for leg in plan.legs:
            suffix = "  (assumed amount)" if leg.assumed_amount else ""
            lines.append(f"  - {plan.side.value} ${leg.quote_amount:,.2f} of {leg.symbol}{suffix}")
        lines.append(f"Total   : ${plan.total_amount:,.2f} per cycle")
    for w in plan.warnings:
        lines.append(f"! {w}")
    return "\n".join(lines)


def execute_plan(plan: Plan, broker=None, dry_run: bool = True) -> list[OrderResult]:
    """Execute ``plan`` legs against ``broker`` (defaults to the paper venue).

    ``dry_run`` returns simulated (unsubmitted) results without touching the
    broker, so callers can preview safely. Passing ``dry_run=False`` submits each
    leg through the broker's ``place_order``.
    """

    from src.trading.models import OrderStatus, OrderType

    results: list[OrderResult] = []
    if dry_run or broker is None:
        for leg in plan.legs:
            results.append(
                OrderResult(
                    order_id="",
                    symbol=leg.symbol,
                    side=plan.side,
                    status=OrderStatus.SIMULATED,
                    provider=plan.provider_id,
                    raw={"quote_amount": leg.quote_amount, "dry_run": True},
                )
            )
        return results

    for leg in plan.legs:
        order = Order(
            symbol=leg.symbol,
            side=plan.side,
            type=OrderType.MARKET,
            quote_amount=leg.quote_amount,
        )
        results.append(broker.place_order(order))
    return results


def _llm_enabled() -> bool:
    return os.getenv("CBDCA_LLM") == "1" and bool(os.getenv("OPENAI_API_KEY"))


def _parse_with_llm(text: str) -> Plan | None:  # pragma: no cover - requires network + key
    """Optional LLM-backed parse. Best-effort; returns None to fall back."""

    try:
        from openai import OpenAI  # type: ignore
    except ImportError:
        return None
    try:
        client = OpenAI()
        schema_hint = (
            "Extract a crypto trading instruction as JSON with keys: provider (string), "
            "side ('buy'|'sell'), frequency (one of hourly/daily/weekly/biweekly/monthly or null), "
            "legs (list of {symbol like 'BTC-USD', quote_amount number})."
        )
        resp = client.chat.completions.create(
            model=os.getenv("CBDCA_LLM_MODEL", "gpt-4o-mini"),
            messages=[
                {"role": "system", "content": schema_hint},
                {"role": "user", "content": text},
            ],
            response_format={"type": "json_object"},
        )
        import json

        data = json.loads(resp.choices[0].message.content)
        side = OrderSide.SELL if str(data.get("side")).lower() == "sell" else OrderSide.BUY
        provider_id, adapter, warnings = _resolve_provider(str(data.get("provider", "")) + " " + text)
        legs = [
            PlanLeg(symbol=leg["symbol"], quote_amount=float(leg["quote_amount"]))
            for leg in data.get("legs", [])
            if leg.get("symbol") and leg.get("quote_amount")
        ]
        return Plan(
            raw_text=text,
            provider_id=provider_id,
            adapter=adapter,
            side=side,
            legs=legs,
            frequency=data.get("frequency"),
            warnings=warnings + ["parsed via LLM"],
        )
    except Exception:
        return None

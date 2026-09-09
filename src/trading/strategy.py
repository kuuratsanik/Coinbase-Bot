"""Recurring-purchase (DCA) schedule model.

Describes *what* to buy and *how often*; the engine decides *when* to act. Kept
separate from execution so it can be serialized, backtested, or driven by any
scheduler (cron, systemd timer, APScheduler, serverless cron).
"""

from __future__ import annotations

from collections.abc import Iterator
from dataclasses import dataclass
from datetime import datetime, timedelta

from dateutil.relativedelta import relativedelta

from src.trading.models import OrderSide

FREQUENCY_STEPS = {
    "daily": timedelta(days=1),
    "weekly": timedelta(days=7),
    "biweekly": timedelta(days=14),
    "monthly": relativedelta(months=1),
}


@dataclass
class ScheduleLeg:
    symbol: str
    quote_amount: float


@dataclass
class Schedule:
    id: str
    provider_id: str
    adapter: str
    legs: list[ScheduleLeg]
    frequency: str
    start: datetime
    side: OrderSide = OrderSide.BUY

    def __post_init__(self) -> None:
        if self.frequency not in FREQUENCY_STEPS:
            raise ValueError(f"invalid frequency '{self.frequency}'; valid: {sorted(FREQUENCY_STEPS)}")
        if not self.legs:
            raise ValueError("schedule requires at least one leg")

    def occurrences(self, until: datetime, limit: int = 10_000) -> Iterator[datetime]:
        """Yield scheduled datetimes from ``start`` up to and including ``until``."""

        step = FREQUENCY_STEPS[self.frequency]
        current = self.start
        count = 0
        while current <= until and count < limit:
            yield current
            current = current + step
            count += 1

    def cycle_key(self, when: datetime) -> str:
        return f"{self.id}:{when.date().isoformat()}"

    @classmethod
    def from_dict(cls, data: dict) -> Schedule:
        legs = [ScheduleLeg(symbol=leg["symbol"], quote_amount=float(leg["quote_amount"])) for leg in data["legs"]]
        start = data["start"]
        start_dt = start if isinstance(start, datetime) else datetime.fromisoformat(str(start))
        return cls(
            id=data["id"],
            provider_id=data.get("provider_id", "paper"),
            adapter=data.get("adapter", "paper"),
            legs=legs,
            frequency=data["frequency"],
            start=start_dt,
            side=OrderSide(data.get("side", "buy")),
        )

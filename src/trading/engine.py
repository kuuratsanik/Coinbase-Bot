"""Idempotent execution of DCA schedules.

Persists which schedule cycles have already run so re-invoking the engine (from a
cron job, a retry, or a crash-restart) never double-buys. This is the core of
turning the old busy-wait loop into a safe, restartable scheduled job.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

from src.trading.base import Broker
from src.trading.logging_config import get_logger, log_event
from src.trading.models import Order, OrderResult, OrderType
from src.trading.strategy import Schedule

_log = get_logger("cbdca.engine")


class StateStore:
    """Tiny JSON-backed store of executed cycle keys (idempotency ledger)."""

    def __init__(self, path: str | Path):
        self.path = Path(path)
        self._data: dict = {"executed": []}
        if self.path.exists():
            try:
                self._data = json.loads(self.path.read_text())
            except (json.JSONDecodeError, OSError):
                self._data = {"executed": []}
        self._data.setdefault("executed", [])

    def has_cycle(self, key: str) -> bool:
        return key in self._data["executed"]

    def record_cycle(self, key: str) -> None:
        if key not in self._data["executed"]:
            self._data["executed"].append(key)
            self._save()

    def _save(self) -> None:
        self.path.write_text(json.dumps(self._data, indent=2))


@dataclass
class CycleExecution:
    cycle_key: str
    when: datetime
    results: list[OrderResult] = field(default_factory=list)
    skipped: bool = False


def run_due(
    schedule: Schedule,
    broker: Broker,
    store: StateStore | None = None,
    now: datetime | None = None,
    dry_run: bool = False,
) -> list[CycleExecution]:
    """Execute every due, not-yet-run cycle of ``schedule`` up to ``now``.

    With a ``store``, already-executed cycles are skipped (idempotent). With
    ``dry_run`` no orders are placed and nothing is recorded.
    """

    now = now or datetime.now()
    executions: list[CycleExecution] = []
    for when in schedule.occurrences(now):
        key = schedule.cycle_key(when)
        if store is not None and store.has_cycle(key):
            executions.append(CycleExecution(cycle_key=key, when=when, skipped=True))
            continue
        results: list[OrderResult] = []
        if not dry_run:
            for leg in schedule.legs:
                order = Order(
                    symbol=leg.symbol,
                    side=schedule.side,
                    type=OrderType.MARKET,
                    quote_amount=leg.quote_amount,
                )
                result = broker.place_order(order)
                results.append(result)
                log_event(
                    _log,
                    logging.INFO,
                    "cycle_order",
                    schedule=schedule.id,
                    cycle=key,
                    symbol=leg.symbol,
                    amount=leg.quote_amount,
                    status=result.status.value,
                    provider=result.provider,
                )
            if store is not None:
                store.record_cycle(key)
        executions.append(CycleExecution(cycle_key=key, when=when, results=results))
    return executions

"""Deterministic DCA backtester.

Simulates a recurring buy schedule over a price series and reports performance,
so a user can preview a strategy before committing real funds. Prices can be
supplied explicitly (e.g. from a data provider) or generated deterministically,
keeping results reproducible and unit-testable offline.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass


@dataclass
class BacktestResult:
    symbol: str
    periods: int
    invested: float
    fees: float
    units: float
    average_cost: float
    final_price: float

    @property
    def market_value(self) -> float:
        return round(self.units * self.final_price, 2)

    @property
    def pnl(self) -> float:
        return round(self.market_value - self.invested, 2)

    @property
    def pnl_pct(self) -> float:
        return round((self.pnl / self.invested) * 100, 2) if self.invested else 0.0

    def as_dict(self) -> dict:
        return {
            "symbol": self.symbol,
            "periods": self.periods,
            "invested": round(self.invested, 2),
            "fees": round(self.fees, 2),
            "units": round(self.units, 10),
            "average_cost": round(self.average_cost, 2),
            "final_price": round(self.final_price, 2),
            "market_value": self.market_value,
            "pnl": self.pnl,
            "pnl_pct": self.pnl_pct,
        }


@dataclass
class DCABacktester:
    """Buy a fixed quote amount each period at the period's price."""

    amount_per_period: float
    fee_rate: float = 0.006

    def run(self, symbol: str, prices: Sequence[float]) -> BacktestResult:
        if self.amount_per_period <= 0:
            raise ValueError("amount_per_period must be positive")
        prices = [float(p) for p in prices if p and p > 0]
        if not prices:
            raise ValueError("prices must contain at least one positive value")

        invested = 0.0
        fees = 0.0
        units = 0.0
        for price in prices:
            spend = self.amount_per_period
            fee = spend * self.fee_rate
            units += spend / price
            invested += spend
            fees += fee
        average_cost = invested / units if units else 0.0
        return BacktestResult(
            symbol=symbol.upper(),
            periods=len(prices),
            invested=invested,
            fees=fees,
            units=units,
            average_cost=average_cost,
            final_price=prices[-1],
        )


def synthetic_series(symbol: str, periods: int, start: float = 100.0, drift: float = 0.01) -> list[float]:
    """A reproducible price path for demos and tests (no randomness)."""

    series: list[float] = []
    price = start
    for i in range(periods):
        # Gentle deterministic oscillation around an upward drift.
        seasonal = 1 + 0.05 * ((i % 4) - 1.5) / 1.5
        price = round(start * ((1 + drift) ** i) * seasonal, 2)
        series.append(price)
    return series

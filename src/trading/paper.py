"""Offline paper-trading engine.

Deterministic, dependency-free, and credential-free: prices are derived from the
symbol (and optionally the date) so tests and demos are reproducible. This is the
default venue so the whole toolkit runs end-to-end anywhere.
"""

from __future__ import annotations

import hashlib
from datetime import date
from typing import Optional

from src.trading.base import Broker, MarketData
from src.trading.models import (
    Balance,
    Order,
    OrderResult,
    OrderSide,
    OrderStatus,
    OrderType,
    Quote,
)
from src.trading.registry import register_broker


def _symbol_base_price(symbol: str) -> float:
    digest = hashlib.sha256(symbol.upper().encode()).hexdigest()
    n = int(digest[:8], 16)
    # Spread prices across a plausible range (~$5 .. ~$65,000).
    return round(5 + (n % 6_500_000) / 100.0, 2)


class PaperMarketData(MarketData):
    id = "paper"
    name = "Paper market data"

    def __init__(self, use_date_drift: bool = True):
        self.use_date_drift = use_date_drift

    def get_price(self, symbol: str) -> Quote:
        price = _symbol_base_price(symbol)
        if self.use_date_drift:
            seed = int(hashlib.sha256(f"{symbol}:{date.today().isoformat()}".encode()).hexdigest()[:6], 16)
            drift = 1 + ((seed % 400) - 200) / 10_000.0  # +/- 2%
            price = round(price * drift, 2)
        return Quote(symbol=symbol.upper(), price=price)


class PaperBroker(Broker):
    """In-memory simulated exchange.

    Starts with ``cash`` units of the quote currency and fills market orders at
    the current paper price minus a taker ``fee_rate``. Balances update in place
    so a session can place several orders and inspect the resulting portfolio.
    """

    id = "paper"
    name = "Paper trading (offline simulator)"
    paper = True

    def __init__(
        self,
        cash: float = 100_000.0,
        quote_currency: str = "USD",
        fee_rate: float = 0.006,
        market_data: Optional[PaperMarketData] = None,
        probe: bool = False,
    ):
        self.quote_currency = quote_currency
        self.fee_rate = fee_rate
        self.market_data = market_data or PaperMarketData()
        self._cash = float(cash)
        self._positions: dict[str, float] = {}

    def get_quote(self, symbol: str) -> Quote:
        return self.market_data.get_price(symbol)

    def _base_asset(self, symbol: str) -> str:
        return symbol.upper().split("-")[0].split("/")[0]

    def place_order(self, order: Order) -> OrderResult:
        order.validate()
        if order.side is not OrderSide.BUY:
            # Sales are supported symmetrically; keep the DCA happy-path first.
            return self._sell(order)
        return self._buy(order)

    def _buy(self, order: Order) -> OrderResult:
        price = order.limit_price if order.type is OrderType.LIMIT and order.limit_price else self.get_quote(order.symbol).price
        if order.quote_amount is not None:
            spend = float(order.quote_amount)
            size = spend / price
        else:
            size = float(order.base_size)
            spend = size * price
        fee = round(spend * self.fee_rate, 2)
        total = spend + fee
        if total > self._cash + 1e-9:
            return OrderResult(
                order_id="", symbol=order.symbol.upper(), side=order.side,
                status=OrderStatus.REJECTED, provider=self.id,
                client_order_id=order.client_order_id,
                raw={"reason": "insufficient paper funds", "needed": round(total, 2), "cash": round(self._cash, 2)},
            )
        self._cash -= total
        base = self._base_asset(order.symbol)
        self._positions[base] = self._positions.get(base, 0.0) + size
        return OrderResult(
            order_id=order.client_order_id, symbol=order.symbol.upper(), side=order.side,
            status=OrderStatus.FILLED, filled_size=round(size, 10), avg_price=round(price, 2),
            fee=fee, provider=self.id, client_order_id=order.client_order_id,
            raw={"spend": round(spend, 2), "cash_after": round(self._cash, 2)},
        )

    def _sell(self, order: Order) -> OrderResult:
        price = self.get_quote(order.symbol).price
        base = self._base_asset(order.symbol)
        held = self._positions.get(base, 0.0)
        size = float(order.base_size) if order.base_size is not None else float(order.quote_amount) / price
        if size > held + 1e-9:
            return OrderResult(
                order_id="", symbol=order.symbol.upper(), side=order.side,
                status=OrderStatus.REJECTED, provider=self.id, client_order_id=order.client_order_id,
                raw={"reason": "insufficient position", "held": held, "requested": size},
            )
        proceeds = size * price
        fee = round(proceeds * self.fee_rate, 2)
        self._positions[base] = held - size
        self._cash += proceeds - fee
        return OrderResult(
            order_id=order.client_order_id, symbol=order.symbol.upper(), side=order.side,
            status=OrderStatus.FILLED, filled_size=round(size, 10), avg_price=round(price, 2),
            fee=fee, provider=self.id, client_order_id=order.client_order_id,
            raw={"proceeds": round(proceeds, 2), "cash_after": round(self._cash, 2)},
        )

    def get_balances(self) -> list[Balance]:
        balances = [Balance(currency=self.quote_currency, total=round(self._cash, 2), available=round(self._cash, 2))]
        for asset, size in sorted(self._positions.items()):
            if size > 0:
                balances.append(Balance(currency=asset, total=round(size, 10), available=round(size, 10)))
        return balances


@register_broker("paper")
def _make_paper(probe: bool = False, **config) -> PaperBroker:
    if probe:
        return PaperBroker(probe=True)
    return PaperBroker(**config)

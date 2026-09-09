"""Abstract adapter interfaces.

Every integration implements one (or more) of these small protocols, so the
CLI, planner, and tests can treat any venue uniformly regardless of whether it
is a paper engine, a ccxt-backed exchange, or a native SDK.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Sequence

from src.trading.models import Balance, Order, OrderResult, Quote


class Broker(ABC):
    """Something that can price and execute orders."""

    #: Stable identifier, matches the catalog entry id where applicable.
    id: str = "broker"
    #: Human-readable name.
    name: str = "Broker"
    #: True when trades are simulated and move no real funds.
    paper: bool = False

    @abstractmethod
    def get_quote(self, symbol: str) -> Quote:
        ...

    @abstractmethod
    def place_order(self, order: Order) -> OrderResult:
        ...

    def get_balances(self) -> Sequence[Balance]:
        return []


class MarketData(ABC):
    """A read-only source of prices."""

    id: str = "marketdata"
    name: str = "Market data"

    @abstractmethod
    def get_price(self, symbol: str) -> Quote:
        ...


class Notifier(ABC):
    """A destination for order/fill confirmations and alerts."""

    id: str = "notifier"
    name: str = "Notifier"

    @abstractmethod
    def notify(self, subject: str, message: str) -> bool:
        ...

"""Shared domain models used by every provider adapter.

Dataclasses + enums keep the core dependency-free while giving adapters a stable
contract to map their venue-specific payloads onto.
"""

from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class AssetClass(str, Enum):
    CRYPTO = "crypto"
    EQUITY = "equity"
    ETF = "etf"
    OPTION = "option"
    FUTURE = "future"
    FOREX = "forex"
    CFD = "cfd"
    BOND = "bond"


class OrderSide(str, Enum):
    BUY = "buy"
    SELL = "sell"


class OrderType(str, Enum):
    MARKET = "market"
    LIMIT = "limit"


class OrderStatus(str, Enum):
    FILLED = "filled"
    ACCEPTED = "accepted"
    REJECTED = "rejected"
    SIMULATED = "simulated"


def new_client_order_id() -> str:
    """Idempotency key so a retried request cannot place a duplicate order."""

    return f"cbdca-{uuid.uuid4().hex[:16]}"


@dataclass
class Order:
    """A request to trade a symbol.

    Exactly one of ``quote_amount`` (spend N of the quote currency, e.g. USD) or
    ``base_size`` (acquire N of the base asset) should be provided.
    """

    symbol: str
    side: OrderSide = OrderSide.BUY
    type: OrderType = OrderType.MARKET
    quote_amount: float | None = None
    base_size: float | None = None
    limit_price: float | None = None
    client_order_id: str = field(default_factory=new_client_order_id)

    def validate(self) -> None:
        if not self.symbol or not isinstance(self.symbol, str):
            raise ValueError("order.symbol must be a non-empty string")
        if (self.quote_amount is None) == (self.base_size is None):
            raise ValueError("provide exactly one of quote_amount or base_size")
        for name in ("quote_amount", "base_size"):
            value = getattr(self, name)
            if value is not None and (not isinstance(value, (int, float)) or value <= 0):
                raise ValueError(f"order.{name} must be a positive number")
        if self.type is OrderType.LIMIT and not self.limit_price:
            raise ValueError("limit orders require a limit_price")


@dataclass
class OrderResult:
    """Normalized outcome of placing an order."""

    order_id: str
    symbol: str
    side: OrderSide
    status: OrderStatus
    filled_size: float = 0.0
    avg_price: float = 0.0
    fee: float = 0.0
    provider: str = ""
    client_order_id: str = ""
    raw: dict[str, Any] = field(default_factory=dict)

    @property
    def notional(self) -> float:
        return round(self.filled_size * self.avg_price, 2)


@dataclass
class Quote:
    symbol: str
    price: float
    ts: float = field(default_factory=time.time)


@dataclass
class Balance:
    currency: str
    total: float
    available: float

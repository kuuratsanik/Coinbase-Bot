"""Native Coinbase Advanced Trade adapter (coinbase-advanced-py).

This is the modern replacement for the project's original Coinbase Pro code.
Auth uses CDP API keys (Ed25519 recommended / ECDSA legacy) handled by the SDK.
Optional dependency:

    pip install coinbase-advanced-py

Credentials come from COINBASE_API_KEY / COINBASE_API_SECRET (or explicit args).
"""

from __future__ import annotations

import os

from src.trading.base import Broker
from src.trading.models import Order, OrderResult, OrderSide, OrderStatus, Quote
from src.trading.registry import _MissingDependency, register_broker


def _import_rest_client():
    try:
        from coinbase.rest import RESTClient  # type: ignore
    except ImportError as exc:  # pragma: no cover - exercised only without SDK
        raise _MissingDependency(
            "coinbase-advanced-py is not installed. Run `pip install coinbase-advanced-py`."
        ) from exc
    return RESTClient


class CoinbaseAdvancedBroker(Broker):
    id = "coinbase"
    name = "Coinbase Advanced Trade"
    paper = False

    def __init__(self, api_key: str = "", api_secret: str = ""):
        RESTClient = _import_rest_client()
        self._client = RESTClient(
            api_key=api_key or os.getenv("COINBASE_API_KEY", ""),
            api_secret=api_secret or os.getenv("COINBASE_API_SECRET", ""),
        )

    def get_quote(self, symbol: str) -> Quote:
        product = self._client.get_product(symbol)
        return Quote(symbol=symbol, price=float(product["price"]))

    def place_order(self, order: Order) -> OrderResult:
        order.validate()
        if order.side is not OrderSide.BUY:
            raise NotImplementedError("sell not wired in this reference adapter")
        # Advanced Trade market buys are denominated in quote size (e.g. USD).
        quote_size = str(order.quote_amount if order.quote_amount is not None else 0)
        result = self._client.market_order_buy(
            client_order_id=order.client_order_id,
            product_id=order.symbol,
            quote_size=quote_size,
        )
        success = bool(getattr(result, "success", False) or (isinstance(result, dict) and result.get("success")))
        return OrderResult(
            order_id=order.client_order_id,
            symbol=order.symbol,
            side=order.side,
            status=OrderStatus.ACCEPTED if success else OrderStatus.REJECTED,
            provider=self.id,
            client_order_id=order.client_order_id,
            raw=result if isinstance(result, dict) else {"success": success},
        )


@register_broker("coinbase")
def _make_coinbase(probe: bool = False, **config) -> CoinbaseAdvancedBroker:
    _import_rest_client()
    if probe:
        return CoinbaseAdvancedBroker.__new__(CoinbaseAdvancedBroker)  # type: ignore[return-value]
    return CoinbaseAdvancedBroker(**config)

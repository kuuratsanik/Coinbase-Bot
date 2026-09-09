"""Generic crypto adapter backed by ccxt.

A single implementation unlocks ~100 crypto exchanges from the catalog. ccxt is
optional: the factory raises a clear, actionable error if it is not installed,
and construction never requires network or keys (keys are only needed to place a
real order or read private balances).

    pip install ccxt
"""

from __future__ import annotations

from src.trading.base import Broker
from src.trading.models import Order, OrderResult, OrderSide, OrderStatus, OrderType, Quote
from src.trading.registry import _MissingDependency, register_broker


def _import_ccxt():
    try:
        import ccxt  # type: ignore
    except ImportError as exc:  # pragma: no cover - exercised only without ccxt
        raise _MissingDependency("ccxt is not installed. Run `pip install ccxt` to enable this venue.") from exc
    return ccxt


class CcxtBroker(Broker):
    """Wrap any ccxt exchange behind the common Broker interface."""

    paper = False

    def __init__(
        self,
        exchange_id: str = "coinbase",
        api_key: str = "",
        secret: str = "",
        password: str = "",
        sandbox: bool = False,
    ):
        self.id = exchange_id
        self.name = f"ccxt:{exchange_id}"
        self.exchange_id = exchange_id
        ccxt = _import_ccxt()
        if not hasattr(ccxt, exchange_id):
            raise ValueError(f"ccxt has no exchange '{exchange_id}'")
        params: dict[str, object] = {"enableRateLimit": True}
        if api_key:
            params["apiKey"] = api_key
        if secret:
            params["secret"] = secret
        if password:
            params["password"] = password
        self._client = getattr(ccxt, exchange_id)(params)
        if sandbox and self._client.has.get("sandbox"):
            self._client.set_sandbox_mode(True)

    def get_quote(self, symbol: str) -> Quote:
        ticker = self._client.fetch_ticker(symbol)
        return Quote(symbol=symbol, price=float(ticker["last"]))

    def place_order(self, order: Order) -> OrderResult:
        order.validate()
        side = "buy" if order.side is OrderSide.BUY else "sell"
        otype = "market" if order.type is OrderType.MARKET else "limit"
        params: dict = {}
        if order.quote_amount is not None:
            params["cost"] = order.quote_amount
            amount = None
        else:
            amount = order.base_size
        result = self._client.create_order(
            symbol=order.symbol,
            type=otype,
            side=side,
            amount=amount,
            price=order.limit_price,
            params=params,
        )
        return OrderResult(
            order_id=str(result.get("id", "")),
            symbol=order.symbol,
            side=order.side,
            status=OrderStatus.ACCEPTED,
            filled_size=float(result.get("filled") or 0.0),
            avg_price=float(result.get("average") or 0.0),
            provider=self.exchange_id,
            client_order_id=order.client_order_id,
            raw=result,
        )


@register_broker("ccxt")
def _make_ccxt(probe: bool = False, exchange_id: str | None = None, **config) -> CcxtBroker:
    # Probe only checks that the optional dependency imports.
    _import_ccxt()
    if probe:
        return CcxtBroker.__new__(CcxtBroker)  # type: ignore[return-value]
    return CcxtBroker(exchange_id=exchange_id or "coinbase", **config)

"""Alpaca adapter (equities, ETFs, options, crypto) with a real paper sandbox.

Uses only the standard library (``urllib``) so it needs no extra install, and its
HTTP transport is injectable, which makes it fully unit-testable offline while
still speaking Alpaca's real REST contract.

Credentials come from ``ALPACA_API_KEY_ID`` / ``ALPACA_API_SECRET_KEY`` (or the
Alpaca-native ``APCA_*`` names). Paper trading is the default; pass ``paper=False``
for live. Docs: https://docs.alpaca.markets/
"""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from collections.abc import Callable

from src.trading.base import Broker
from src.trading.models import Order, OrderResult, OrderSide, OrderStatus, OrderType, Quote

PAPER_BASE = "https://paper-api.alpaca.markets"
LIVE_BASE = "https://api.alpaca.markets"
DATA_BASE = "https://data.alpaca.markets"

# transport(method, url, headers, body) -> (status_code, parsed_json)
Transport = Callable[[str, str, dict, bytes | None], "tuple[int, dict]"]


def _urllib_transport(method: str, url: str, headers: dict, body: bytes | None) -> tuple[int, dict]:
    req = urllib.request.Request(url, data=body, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:  # noqa: S310 (fixed Alpaca hosts)
            raw = resp.read().decode() or "{}"
            return resp.status, json.loads(raw)
    except urllib.error.HTTPError as exc:  # pragma: no cover - network path
        try:
            return exc.code, json.loads(exc.read().decode() or "{}")
        except (json.JSONDecodeError, OSError):
            return exc.code, {"message": str(exc)}


class AlpacaBroker(Broker):
    id = "alpaca"
    name = "Alpaca"

    def __init__(
        self,
        api_key: str = "",
        api_secret: str = "",
        paper: bool = True,
        transport: Transport | None = None,
        base_url: str | None = None,
        data_url: str = DATA_BASE,
    ):
        self.api_key = api_key or os.getenv("ALPACA_API_KEY_ID") or os.getenv("APCA_API_KEY_ID", "")
        self.api_secret = api_secret or os.getenv("ALPACA_API_SECRET_KEY") or os.getenv("APCA_API_SECRET_KEY", "")
        self.paper = paper
        self.base_url = base_url or (PAPER_BASE if paper else LIVE_BASE)
        self.data_url = data_url
        self._transport = transport or _urllib_transport

    def _headers(self) -> dict:
        return {
            "APCA-API-KEY-ID": self.api_key,
            "APCA-API-SECRET-KEY": self.api_secret,
            "Content-Type": "application/json",
        }

    def _request(self, method: str, url: str, body: dict | None = None) -> dict:
        payload = json.dumps(body).encode() if body is not None else None
        status, data = self._transport(method, url, self._headers(), payload)
        if not 200 <= status < 300:
            raise RuntimeError(f"Alpaca API error {status}: {data.get('message', data)}")
        return data

    def get_quote(self, symbol: str) -> Quote:
        if "/" in symbol:  # crypto pair, e.g. BTC/USD
            data = self._request("GET", f"{self.data_url}/v1beta3/crypto/us/latest/trades?symbols={symbol}")
            price = float(data["trades"][symbol]["p"])
        else:
            data = self._request("GET", f"{self.data_url}/v2/stocks/{symbol}/trades/latest")
            price = float(data["trade"]["p"])
        return Quote(symbol=symbol, price=price)

    def place_order(self, order: Order) -> OrderResult:
        order.validate()
        body: dict = {
            "symbol": order.symbol,
            "side": "buy" if order.side is OrderSide.BUY else "sell",
            "type": "market" if order.type is OrderType.MARKET else "limit",
            "time_in_force": "day",
            "client_order_id": order.client_order_id,
        }
        if order.quote_amount is not None:
            body["notional"] = str(order.quote_amount)
        else:
            body["qty"] = str(order.base_size)
        if order.type is OrderType.LIMIT and order.limit_price:
            body["limit_price"] = str(order.limit_price)

        data = self._request("POST", f"{self.base_url}/v2/orders", body=body)
        status_str = str(data.get("status", "")).lower()
        mapped = OrderStatus.FILLED if status_str == "filled" else OrderStatus.ACCEPTED
        return OrderResult(
            order_id=str(data.get("id", "")),
            symbol=order.symbol,
            side=order.side,
            status=mapped,
            filled_size=float(data.get("filled_qty") or 0.0),
            avg_price=float(data.get("filled_avg_price") or 0.0),
            provider=self.id,
            client_order_id=order.client_order_id,
            raw=data,
        )


# Registered at import time via registry's adapter import block.
def register() -> None:
    from src.trading.registry import register_broker

    @register_broker("alpaca")
    def _make_alpaca(probe: bool = False, **config) -> AlpacaBroker:
        if probe:
            return AlpacaBroker.__new__(AlpacaBroker)  # type: ignore[return-value]
        return AlpacaBroker(**config)


register()

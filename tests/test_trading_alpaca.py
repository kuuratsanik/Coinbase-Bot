import json

import pytest

from src.trading import catalog, registry
from src.trading.alpaca_adapter import AlpacaBroker
from src.trading.models import Order, OrderSide, OrderStatus, OrderType


class FakeTransport:
    """Records the last request and returns a canned (status, dict) response."""

    def __init__(self, status=200, response=None):
        self.status = status
        self.response = response or {}
        self.calls = []

    def __call__(self, method, url, headers, body):
        parsed = json.loads(body.decode()) if body else None
        self.calls.append({"method": method, "url": url, "headers": headers, "body": parsed})
        return self.status, self.response

    @property
    def last(self):
        return self.calls[-1]


class TestAlpacaPlaceOrder:
    def test_notional_market_buy_body(self):
        t = FakeTransport(response={"id": "abc", "status": "accepted"})
        broker = AlpacaBroker(api_key="k", api_secret="s", transport=t)
        order = Order(symbol="AAPL", side=OrderSide.BUY, quote_amount=100.0)
        result = broker.place_order(order)

        body = t.last["body"]
        assert body["symbol"] == "AAPL"
        assert body["side"] == "buy"
        assert body["type"] == "market"
        assert body["time_in_force"] == "day"
        assert body["notional"] == "100.0"
        assert "qty" not in body
        assert body["client_order_id"] == order.client_order_id
        assert t.last["method"] == "POST"
        assert t.last["url"].endswith("/v2/orders")
        assert result.status is OrderStatus.ACCEPTED

    def test_qty_when_base_size(self):
        t = FakeTransport(response={"id": "abc", "status": "accepted"})
        broker = AlpacaBroker(api_key="k", api_secret="s", transport=t)
        broker.place_order(Order(symbol="AAPL", side=OrderSide.SELL, base_size=3.0))
        body = t.last["body"]
        assert body["qty"] == "3.0"
        assert body["side"] == "sell"
        assert "notional" not in body

    def test_filled_status_mapped(self):
        t = FakeTransport(response={"id": "x", "status": "filled", "filled_qty": "0.5", "filled_avg_price": "200"})
        broker = AlpacaBroker(api_key="k", api_secret="s", transport=t)
        result = broker.place_order(Order(symbol="AAPL", quote_amount=100.0))
        assert result.status is OrderStatus.FILLED
        assert result.filled_size == pytest.approx(0.5)
        assert result.avg_price == pytest.approx(200.0)

    def test_limit_order_includes_price(self):
        t = FakeTransport(response={"id": "x", "status": "accepted"})
        broker = AlpacaBroker(api_key="k", api_secret="s", transport=t)
        broker.place_order(Order(symbol="AAPL", type=OrderType.LIMIT, quote_amount=100.0, limit_price=150.0))
        body = t.last["body"]
        assert body["type"] == "limit"
        assert body["limit_price"] == "150.0"


class TestAlpacaQuotes:
    def test_equity_quote_parsed(self):
        t = FakeTransport(response={"trade": {"p": 191.23}})
        broker = AlpacaBroker(api_key="k", api_secret="s", transport=t)
        quote = broker.get_quote("AAPL")
        assert quote.price == pytest.approx(191.23)
        assert "/v2/stocks/AAPL/trades/latest" in t.last["url"]

    def test_crypto_quote_parsed(self):
        t = FakeTransport(response={"trades": {"BTC/USD": {"p": 65000.0}}})
        broker = AlpacaBroker(api_key="k", api_secret="s", transport=t)
        quote = broker.get_quote("BTC/USD")
        assert quote.price == pytest.approx(65000.0)
        assert "/v1beta3/crypto/us/latest/trades" in t.last["url"]


class TestAlpacaErrors:
    def test_non_2xx_raises(self):
        t = FakeTransport(status=403, response={"message": "forbidden"})
        broker = AlpacaBroker(api_key="k", api_secret="s", transport=t)
        with pytest.raises(RuntimeError):
            broker.get_quote("AAPL")


class TestAlpacaRegistration:
    def test_registry_creates_with_transport(self):
        t = FakeTransport(response={"trade": {"p": 10.0}})
        broker = registry.create_broker("alpaca", transport=t)
        assert isinstance(broker, AlpacaBroker)
        assert broker.get_quote("AAPL").price == pytest.approx(10.0)

    def test_paper_default(self):
        broker = AlpacaBroker(api_key="k", api_secret="s")
        assert broker.paper is True
        assert broker.base_url.startswith("https://paper-api.alpaca.markets")

    def test_catalog_entry_graduated(self):
        svc = catalog.get("alpaca")
        assert svc is not None
        assert svc.adapter == "alpaca"

    def test_availability(self):
        runnable, _ = registry.broker_availability("alpaca")
        assert runnable is True

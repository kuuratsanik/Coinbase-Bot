import pytest

from src.trading import registry
from src.trading.models import Order, OrderSide, OrderStatus, OrderType
from src.trading.paper import PaperBroker, PaperMarketData


class TestPaperMarketData:
    def test_price_is_positive_and_deterministic(self):
        md = PaperMarketData(use_date_drift=False)
        p1 = md.get_price("BTC-USD").price
        p2 = md.get_price("BTC-USD").price
        assert p1 > 0
        assert p1 == p2

    def test_distinct_symbols_have_distinct_prices(self):
        md = PaperMarketData(use_date_drift=False)
        assert md.get_price("BTC-USD").price != md.get_price("ETH-USD").price


class TestPaperBroker:
    def test_market_buy_updates_cash_and_position(self):
        broker = PaperBroker(cash=1000.0, fee_rate=0.0, market_data=PaperMarketData(use_date_drift=False))
        result = broker.place_order(Order(symbol="BTC-USD", quote_amount=100.0))
        assert result.status is OrderStatus.FILLED
        assert result.filled_size > 0
        balances = {b.currency: b.total for b in broker.get_balances()}
        assert balances["USD"] == pytest.approx(900.0, abs=1e-6)
        assert balances["BTC"] == pytest.approx(result.filled_size, abs=1e-9)

    def test_fee_is_applied(self):
        broker = PaperBroker(cash=1000.0, fee_rate=0.01, market_data=PaperMarketData(use_date_drift=False))
        result = broker.place_order(Order(symbol="BTC-USD", quote_amount=100.0))
        assert result.fee == pytest.approx(1.0, abs=1e-6)
        usd = next(b.total for b in broker.get_balances() if b.currency == "USD")
        assert usd == pytest.approx(899.0, abs=1e-6)

    def test_insufficient_funds_rejected(self):
        broker = PaperBroker(cash=10.0, market_data=PaperMarketData(use_date_drift=False))
        result = broker.place_order(Order(symbol="BTC-USD", quote_amount=100.0))
        assert result.status is OrderStatus.REJECTED
        assert result.raw["reason"] == "insufficient paper funds"

    def test_buy_then_sell_roundtrip(self):
        broker = PaperBroker(cash=1000.0, fee_rate=0.0, market_data=PaperMarketData(use_date_drift=False))
        broker.place_order(Order(symbol="ETH-USD", quote_amount=200.0))
        held = next(b.total for b in broker.get_balances() if b.currency == "ETH")
        sell = broker.place_order(Order(symbol="ETH-USD", side=OrderSide.SELL, base_size=held))
        assert sell.status is OrderStatus.FILLED
        eth_left = [b for b in broker.get_balances() if b.currency == "ETH"]
        assert eth_left == [] or eth_left[0].total == pytest.approx(0.0, abs=1e-9)

    def test_oversell_rejected(self):
        broker = PaperBroker(cash=1000.0, market_data=PaperMarketData(use_date_drift=False))
        result = broker.place_order(Order(symbol="BTC-USD", side=OrderSide.SELL, base_size=5.0))
        assert result.status is OrderStatus.REJECTED

    def test_invalid_order_raises(self):
        broker = PaperBroker()
        with pytest.raises(ValueError):
            broker.place_order(Order(symbol="BTC-USD"))  # neither amount nor size
        with pytest.raises(ValueError):
            broker.place_order(Order(symbol="BTC-USD", quote_amount=-5.0))

    def test_registry_creates_paper_broker(self):
        broker = registry.create_broker("paper", cash=500.0)
        assert broker.paper is True
        assert broker.get_quote("BTC-USD").price > 0

    def test_paper_adapter_reported_available(self):
        runnable, reason = registry.broker_availability("paper")
        assert runnable is True
        assert reason is None

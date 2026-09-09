import pytest

from src.trading.ai import execute_plan, format_plan, parse
from src.trading.models import OrderSide, OrderStatus
from src.trading.paper import PaperBroker, PaperMarketData


class TestPlanner:
    def test_single_amount_applies_to_all_assets(self):
        plan = parse("DCA $50 of BTC and ETH weekly on coinbase")
        assert plan.provider_id == "coinbase"
        assert plan.adapter == "coinbase"
        assert plan.frequency == "weekly"
        assert plan.side is OrderSide.BUY
        symbols = {leg.symbol: leg.quote_amount for leg in plan.legs}
        assert symbols == {"BTC-USD": 50.0, "ETH-USD": 50.0}
        assert plan.total_amount == 100.0

    def test_positional_amounts(self):
        plan = parse("buy $50 BTC and $100 ETH")
        symbols = {leg.symbol: leg.quote_amount for leg in plan.legs}
        assert symbols == {"BTC-USD": 50.0, "ETH-USD": 100.0}

    def test_explicit_pairs(self):
        plan = parse("put $30 of SOL and $70 of ADA in")
        symbols = {leg.symbol: leg.quote_amount for leg in plan.legs}
        assert symbols == {"SOL-USD": 30.0, "ADA-USD": 70.0}

    def test_no_amount_assumes_default_with_warning(self):
        plan = parse("buy some SOL and ADA on kraken")
        assert plan.provider_id == "kraken"
        assert all(leg.assumed_amount for leg in plan.legs)
        assert all(leg.quote_amount == 100.0 for leg in plan.legs)
        assert any("assuming" in w.lower() for w in plan.warnings)

    def test_sell_side_detected(self):
        plan = parse("sell $100 of BTC")
        assert plan.side is OrderSide.SELL

    def test_provider_defaults_to_paper(self):
        plan = parse("buy $10 of BTC")
        assert plan.provider_id == "paper"
        assert plan.adapter == "paper"

    def test_catalog_only_provider_falls_back_to_paper_adapter(self):
        plan = parse("buy $10 of BTC on uniswap")
        assert plan.provider_id == "uniswap"
        assert plan.adapter == "paper"
        assert any("no bundled adapter" in w for w in plan.warnings)

    def test_unparseable_request_is_not_actionable(self):
        plan = parse("hello there, nice weather today")
        assert not plan.is_actionable
        assert plan.warnings

    def test_format_plan_contains_key_details(self):
        text = format_plan(parse("DCA $50 of BTC and ETH weekly on coinbase"))
        assert "coinbase" in text
        assert "BTC-USD" in text and "ETH-USD" in text
        assert "weekly" in text

    def test_execute_dry_run_does_not_touch_broker(self):
        plan = parse("buy $50 of BTC and ETH")
        results = execute_plan(plan, broker=None, dry_run=True)
        assert len(results) == 2
        assert all(r.status is OrderStatus.SIMULATED for r in results)

    def test_execute_on_paper_broker_fills(self):
        plan = parse("buy $50 of BTC and ETH")
        broker = PaperBroker(cash=1000.0, market_data=PaperMarketData(use_date_drift=False))
        results = execute_plan(plan, broker=broker, dry_run=False)
        assert len(results) == 2
        assert all(r.status is OrderStatus.FILLED for r in results)
        currencies = {b.currency for b in broker.get_balances()}
        assert {"BTC", "ETH"}.issubset(currencies)

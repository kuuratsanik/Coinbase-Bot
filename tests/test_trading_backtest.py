import pytest

from src.trading.backtest import BacktestResult, DCABacktester, synthetic_series


class TestSyntheticSeries:
    def test_length_matches_periods(self):
        assert len(synthetic_series("BTC-USD", 52)) == 52
        assert synthetic_series("BTC-USD", 0) == []

    def test_deterministic(self):
        a = synthetic_series("BTC-USD", 10, start=100.0, drift=0.02)
        b = synthetic_series("BTC-USD", 10, start=100.0, drift=0.02)
        assert a == b

    def test_all_positive(self):
        assert all(p > 0 for p in synthetic_series("ETH-USD", 30))


class TestDCABacktester:
    def test_invested_and_units_math(self):
        # Flat price of 100 for 4 periods, no fee => easy to reason about.
        result = DCABacktester(amount_per_period=100.0, fee_rate=0.0).run("BTC-USD", [100.0] * 4)
        assert result.periods == 4
        assert result.invested == pytest.approx(400.0)
        assert result.units == pytest.approx(4.0)
        assert result.average_cost == pytest.approx(100.0)
        assert result.fees == pytest.approx(0.0)

    def test_fees_accumulate(self):
        result = DCABacktester(amount_per_period=100.0, fee_rate=0.01).run("BTC-USD", [100.0] * 3)
        assert result.fees == pytest.approx(3.0)

    def test_pnl_positive_when_price_rises(self):
        result = DCABacktester(amount_per_period=100.0, fee_rate=0.0).run("BTC-USD", [100.0, 200.0])
        assert result.final_price == 200.0
        assert result.pnl > 0
        assert result.pnl_pct > 0

    def test_pnl_negative_when_price_falls(self):
        result = DCABacktester(amount_per_period=100.0, fee_rate=0.0).run("BTC-USD", [200.0, 50.0])
        assert result.pnl < 0
        assert result.pnl_pct < 0

    def test_symbol_uppercased(self):
        result = DCABacktester(amount_per_period=10.0).run("btc-usd", [100.0])
        assert result.symbol == "BTC-USD"

    def test_as_dict_keys(self):
        result = DCABacktester(amount_per_period=100.0).run("BTC-USD", [100.0, 110.0])
        data = result.as_dict()
        for key in (
            "symbol",
            "periods",
            "invested",
            "fees",
            "units",
            "average_cost",
            "final_price",
            "market_value",
            "pnl",
            "pnl_pct",
        ):
            assert key in data

    def test_empty_prices_raises(self):
        with pytest.raises(ValueError):
            DCABacktester(amount_per_period=100.0).run("BTC-USD", [])

    def test_all_nonpositive_prices_raises(self):
        with pytest.raises(ValueError):
            DCABacktester(amount_per_period=100.0).run("BTC-USD", [0.0, -5.0])

    def test_nonpositive_amount_raises(self):
        with pytest.raises(ValueError):
            DCABacktester(amount_per_period=0.0).run("BTC-USD", [100.0])

    def test_pnl_pct_zero_when_no_investment(self):
        result = BacktestResult("BTC-USD", 0, invested=0.0, fees=0.0, units=0.0, average_cost=0.0, final_price=100.0)
        assert result.pnl_pct == 0.0

from datetime import datetime

import pytest

from src.trading.engine import CycleExecution, StateStore, run_due
from src.trading.models import OrderSide, OrderStatus
from src.trading.paper import PaperBroker, PaperMarketData
from src.trading.strategy import Schedule, ScheduleLeg


def make_schedule(frequency="weekly", start="2026-01-01"):
    return Schedule(
        id="cli-dca",
        provider_id="paper",
        adapter="paper",
        legs=[ScheduleLeg("BTC-USD", 50.0), ScheduleLeg("ETH-USD", 50.0)],
        frequency=frequency,
        start=datetime.fromisoformat(start),
        side=OrderSide.BUY,
    )


def paper():
    return PaperBroker(cash=100_000.0, market_data=PaperMarketData(use_date_drift=False))


class TestSchedule:
    @pytest.mark.parametrize(
        "frequency,expected",
        [("daily", 31), ("weekly", 5), ("biweekly", 3), ("monthly", 1)],
    )
    def test_occurrences_count(self, frequency, expected):
        sched = make_schedule(frequency=frequency)
        until = datetime(2026, 1, 31)
        assert len(list(sched.occurrences(until))) == expected

    def test_cycle_key_format(self):
        sched = make_schedule()
        key = sched.cycle_key(datetime(2026, 1, 8, 9, 30))
        assert key == "cli-dca:2026-01-08"

    def test_invalid_frequency_raises(self):
        with pytest.raises(ValueError):
            make_schedule(frequency="hourly")

    def test_no_legs_raises(self):
        with pytest.raises(ValueError):
            Schedule(
                id="x", provider_id="paper", adapter="paper", legs=[], frequency="weekly", start=datetime(2026, 1, 1)
            )

    def test_from_dict_roundtrip(self):
        sched = Schedule.from_dict(
            {
                "id": "s1",
                "legs": [{"symbol": "BTC-USD", "quote_amount": 25}],
                "frequency": "monthly",
                "start": "2026-01-01",
            }
        )
        assert sched.id == "s1"
        assert sched.legs[0].quote_amount == 25.0
        assert sched.side is OrderSide.BUY


class TestRunDue:
    def test_executes_due_cycles(self):
        sched = make_schedule()
        broker = paper()
        now = datetime(2026, 1, 31)
        executions = run_due(sched, broker, now=now)
        assert len(executions) == 5
        assert all(not ex.skipped for ex in executions)
        # 2 legs each cycle => 10 order results total.
        assert sum(len(ex.results) for ex in executions) == 10
        assert all(r.status is OrderStatus.FILLED for ex in executions for r in ex.results)

    def test_dry_run_places_nothing(self):
        sched = make_schedule()
        broker = paper()
        now = datetime(2026, 1, 31)
        executions = run_due(sched, broker, now=now, dry_run=True)
        assert all(ex.results == [] for ex in executions)
        # Cash untouched.
        usd = next(b.total for b in broker.get_balances() if b.currency == "USD")
        assert usd == pytest.approx(100_000.0)

    def test_idempotent_second_run_skips(self, tmp_path):
        sched = make_schedule()
        now = datetime(2026, 1, 31)
        state_path = tmp_path / "state.json"

        first = run_due(sched, paper(), StateStore(state_path), now=now)
        assert all(not ex.skipped for ex in first)

        # Fresh broker + a new StateStore reading the same file: nothing re-executes.
        second = run_due(sched, paper(), StateStore(state_path), now=now)
        assert all(ex.skipped for ex in second)
        assert all(ex.results == [] for ex in second)

    def test_dry_run_not_recorded(self, tmp_path):
        sched = make_schedule()
        now = datetime(2026, 1, 31)
        state_path = tmp_path / "state.json"

        run_due(sched, paper(), StateStore(store_path := state_path), now=now, dry_run=True)
        # Dry run records nothing, so a real run afterwards executes everything.
        real = run_due(sched, paper(), StateStore(store_path), now=now)
        assert all(not ex.skipped for ex in real)


class TestStateStore:
    def test_persists_and_reloads(self, tmp_path):
        path = tmp_path / "ledger.json"
        store = StateStore(path)
        assert store.has_cycle("k1") is False
        store.record_cycle("k1")
        assert store.has_cycle("k1") is True
        # A new store reads the persisted file.
        assert StateStore(path).has_cycle("k1") is True

    def test_corrupt_file_resets(self, tmp_path):
        path = tmp_path / "ledger.json"
        path.write_text("{not valid json")
        store = StateStore(path)
        assert store.has_cycle("anything") is False

    def test_cycle_execution_defaults(self):
        ex = CycleExecution(cycle_key="k", when=datetime(2026, 1, 1))
        assert ex.results == []
        assert ex.skipped is False

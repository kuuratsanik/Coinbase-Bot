import pytest

import trade


def run(capsys, argv):
    code = trade.main(argv)
    out = capsys.readouterr().out
    return code, out


class TestTradeCLI:
    def test_services_lists_catalog(self, capsys):
        code, out = run(capsys, ["services"])
        assert code == 0
        assert "coinbase" in out
        assert "kraken" in out
        assert "catalog:" in out

    def test_services_category_filter(self, capsys):
        code, out = run(capsys, ["services", "--category", "market_data"])
        assert code == 0
        assert "polygon" in out
        assert "coinbase" not in out.split("catalog:")[0]

    def test_services_bad_category(self, capsys):
        code, out = run(capsys, ["services", "--category", "nope"])
        assert code == 2
        assert "Unknown category" in out

    def test_services_search(self, capsys):
        code, out = run(capsys, ["services", "--search", "options"])
        assert code == 0
        assert "deribit" in out

    def test_service_detail(self, capsys):
        code, out = run(capsys, ["service", "coinbase"])
        assert code == 0
        assert "Coinbase Advanced Trade" in out
        assert "adapter" in out

    def test_service_unknown(self, capsys):
        code, out = run(capsys, ["service", "nope"])
        assert code == 2

    def test_providers(self, capsys):
        code, out = run(capsys, ["providers"])
        assert code == 0
        assert "paper" in out
        assert "ready" in out

    def test_quote_paper(self, capsys):
        code, out = run(capsys, ["quote", "--provider", "paper", "BTC-USD"])
        assert code == 0
        assert "BTC-USD" in out and "paper" in out

    def test_buy_paper_fills(self, capsys):
        code, out = run(capsys, ["buy", "--provider", "paper", "--symbol", "BTC-USD", "--amount", "100"])
        assert code == 0
        assert "FILLED" in out
        assert "paper balances" in out

    def test_ask_falls_back_to_paper_and_executes(self, capsys):
        code, out = run(capsys, ["ask", "DCA $50 of BTC and ETH weekly on coinbase"])
        assert code == 0
        assert "BTC-USD" in out and "ETH-USD" in out
        assert "paper" in out.lower()

    def test_ask_unactionable_returns_2(self, capsys):
        code, out = run(capsys, ["ask", "what is the weather"])
        assert code == 2

    def test_buy_catalog_only_provider_errors(self, capsys):
        with pytest.raises(SystemExit):
            trade.main(["buy", "--provider", "uniswap", "--symbol", "ETH-USD", "--amount", "10"])

    def test_backtest_runs(self, capsys):
        code, out = run(capsys, ["backtest", "--symbol", "BTC-USD", "--amount", "100", "--periods", "12"])
        assert code == 0
        assert "DCA backtest" in out
        assert "invested" in out
        assert "pnl" in out

    def test_dca_paper_executes_then_idempotent(self, capsys, tmp_path):
        state = str(tmp_path / "state.json")
        argv = [
            "dca",
            "--provider",
            "paper",
            "--leg",
            "BTC-USD:50",
            "--leg",
            "ETH-USD:50",
            "--frequency",
            "weekly",
            "--start",
            "2026-01-01",
            "--state",
            state,
        ]

        code, out = run(capsys, argv)
        assert code == 0
        assert "FILLED" in out
        assert "0 skipped" in out

        # Second run with the same state file: everything is skipped (idempotent).
        code, out = run(capsys, argv)
        assert code == 0
        assert "SKIPPED" in out
        assert "0 cycle(s) processed" in out

    def test_dca_dry_run_places_nothing(self, capsys):
        code, out = run(
            capsys,
            [
                "dca",
                "--provider",
                "paper",
                "--leg",
                "BTC-USD:50",
                "--frequency",
                "monthly",
                "--start",
                "2026-01-01",
                "--dry-run",
            ],
        )
        assert code == 0
        assert "DRY RUN" in out

    def test_dca_bad_leg_errors(self, capsys):
        with pytest.raises(SystemExit):
            trade.main(
                ["dca", "--provider", "paper", "--leg", "BTCUSD", "--frequency", "weekly", "--start", "2026-01-01"]
            )

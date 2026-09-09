import pytest

from src.trading import catalog
from src.trading.catalog import Category


class TestCatalog:
    def test_catalog_is_nonempty_and_unique_ids(self):
        services = catalog.all_services()
        assert len(services) > 60
        ids = [s.id for s in services]
        assert len(ids) == len(set(ids)), "service ids must be unique"

    def test_paper_is_present_and_first(self):
        assert catalog.all_services()[0].id == "paper"
        paper = catalog.get("paper")
        assert paper is not None
        assert paper.adapter == "paper"
        assert "paper" in paper.capabilities

    def test_get_unknown_returns_none(self):
        assert catalog.get("does-not-exist") is None

    @pytest.mark.parametrize("service_id", ["coinbase", "kraken", "binance", "alpaca", "oanda", "deribit"])
    def test_well_known_services_present(self, service_id):
        assert catalog.get(service_id) is not None

    def test_categories_cover_multiple_domains(self):
        cats = catalog.categories()
        assert Category.CRYPTO_EXCHANGE in cats
        assert Category.BROKER in cats
        assert Category.MARKET_DATA in cats
        assert Category.NOTIFIER in cats
        assert len(cats) >= 10

    def test_by_category_filters(self):
        exchanges = catalog.by_category(Category.CRYPTO_EXCHANGE)
        assert all(s.category == Category.CRYPTO_EXCHANGE for s in exchanges)
        assert any(s.id == "coinbase" for s in exchanges)

    def test_search_matches_capability_and_name(self):
        assert any(s.id == "deribit" for s in catalog.search("options"))
        assert any(s.id == "coinbase" for s in catalog.search("coinbase"))
        assert catalog.search("zzzznotarealthing") == []

    def test_search_empty_returns_all(self):
        assert len(catalog.search("")) == len(catalog.all_services())

    def test_stats(self):
        st = catalog.stats()
        assert st["total"] == len(catalog.all_services())
        assert st["with_adapter"] >= 3

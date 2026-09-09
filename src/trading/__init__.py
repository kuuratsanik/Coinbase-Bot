"""Pluggable multi-provider automated-trading toolkit.

This package turns the project from a single Coinbase-Pro script into an
extensible platform where an end user can:

* browse a catalog of trading/data/notification services and pick one, or
* describe what they want in natural language and let the planner do it.

The core (models, catalog, registry, paper engine, planner) depends only on the
Python standard library so it runs anywhere with no credentials. Real venue
integrations (ccxt, coinbase-advanced-py, HTTP webhooks) are optional and loaded
lazily so a missing extra never breaks the core experience.
"""

from src.trading.models import (
    AssetClass,
    Balance,
    Order,
    OrderResult,
    OrderSide,
    OrderStatus,
    OrderType,
    Quote,
)

__all__ = [
    "AssetClass",
    "Balance",
    "Order",
    "OrderResult",
    "OrderSide",
    "OrderStatus",
    "OrderType",
    "Quote",
]

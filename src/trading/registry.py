"""Registry that turns a catalog ``adapter`` id into a live object.

Adapters register a factory here. Optional integrations (ccxt, coinbase) import
their dependency lazily inside the factory, so importing this module never fails
even when those extras are absent. ``available_brokers()`` probes each factory so
the CLI can show the user what is actually runnable right now vs. what needs an
extra install or credentials.
"""

from __future__ import annotations

from typing import Callable, Optional

from src.trading.base import Broker, Notifier

BrokerFactory = Callable[..., Broker]
NotifierFactory = Callable[..., Notifier]

_BROKER_FACTORIES: dict[str, BrokerFactory] = {}
_NOTIFIER_FACTORIES: dict[str, NotifierFactory] = {}


def register_broker(adapter_id: str) -> Callable[[BrokerFactory], BrokerFactory]:
    def deco(fn: BrokerFactory) -> BrokerFactory:
        _BROKER_FACTORIES[adapter_id] = fn
        return fn

    return deco


def register_notifier(adapter_id: str) -> Callable[[NotifierFactory], NotifierFactory]:
    def deco(fn: NotifierFactory) -> NotifierFactory:
        _NOTIFIER_FACTORIES[adapter_id] = fn
        return fn

    return deco


def create_broker(adapter_id: str, **config) -> Broker:
    if adapter_id not in _BROKER_FACTORIES:
        raise KeyError(
            f"No broker adapter '{adapter_id}'. Registered: {sorted(_BROKER_FACTORIES)}"
        )
    return _BROKER_FACTORIES[adapter_id](**config)


def create_notifier(adapter_id: str, **config) -> Notifier:
    if adapter_id not in _NOTIFIER_FACTORIES:
        raise KeyError(
            f"No notifier adapter '{adapter_id}'. Registered: {sorted(_NOTIFIER_FACTORIES)}"
        )
    return _NOTIFIER_FACTORIES[adapter_id](**config)


def registered_broker_adapters() -> list[str]:
    return sorted(_BROKER_FACTORIES)


def registered_notifier_adapters() -> list[str]:
    return sorted(_NOTIFIER_FACTORIES)


def broker_availability(adapter_id: str) -> tuple[bool, Optional[str]]:
    """Return (is_runnable_now, reason_if_not).

    Runnable means the adapter and any optional dependency import cleanly with no
    credentials required to *construct* it. Credentialed venues still construct
    (they only need keys when placing a real order), so this mostly distinguishes
    "extra not installed" from "ready".
    """

    if adapter_id not in _BROKER_FACTORIES:
        return False, "no adapter registered"
    try:
        _BROKER_FACTORIES[adapter_id](probe=True)
        return True, None
    except _MissingDependency as exc:
        return False, str(exc)
    except Exception:
        # Construction may legitimately require config; the adapter itself imported.
        return True, None


class _MissingDependency(RuntimeError):
    """Raised by an adapter factory when its optional package is not installed."""


# Import adapter modules for their registration side effects. Kept at the bottom
# so the registry API above is fully defined first.
from src.trading import paper as _paper  # noqa: E402,F401
from src.trading import notifiers as _notifiers  # noqa: E402,F401
from src.trading import ccxt_adapter as _ccxt  # noqa: E402,F401
from src.trading import coinbase_adapter as _coinbase  # noqa: E402,F401

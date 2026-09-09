#!/usr/bin/env python3
"""Unified automated-trading CLI.

Pick a service and act, or just ask in plain English:

    python trade.py services                      # browse the whole catalog
    python trade.py services --category crypto_exchange
    python trade.py services --search options
    python trade.py service coinbase              # details for one service
    python trade.py providers                     # adapters runnable right now
    python trade.py quote --provider paper BTC-USD
    python trade.py buy --provider paper --symbol BTC-USD --amount 100
    python trade.py ask "DCA $50 of BTC and ETH weekly on coinbase"

Real venues (Coinbase, Kraken, Binance, ... via ccxt/native SDKs) place orders
only with --execute and valid credentials. The offline 'paper' venue is the
default and moves no real funds.
"""

from __future__ import annotations

import argparse
import sys

from src.trading import catalog
from src.trading import registry
from src.trading.ai import execute_plan, format_plan, parse
from src.trading.models import Order, OrderSide, OrderType


def _fmt_row(cols: list[str], widths: list[int]) -> str:
    return "  ".join(c.ljust(w) for c, w in zip(cols, widths)).rstrip()


def _print_services(services: list[catalog.Service]) -> None:
    if not services:
        print("No services match.")
        return
    headers = ["ID", "NAME", "CATEGORY", "ASSETS", "ADAPTER"]
    rows = []
    for s in services:
        assets = ",".join(a.value for a in s.assets) or "-"
        rows.append([s.id, s.name, s.category.value, assets, s.available_via])
    widths = [max(len(h), *(len(r[i]) for r in rows)) for i, h in enumerate(headers)]
    print(_fmt_row(headers, widths))
    print(_fmt_row(["-" * w for w in widths], widths))
    for r in rows:
        print(_fmt_row(r, widths))
    st = catalog.stats()
    print(f"\n{len(services)} shown | catalog: {st['total']} services, "
          f"{st['categories']} categories, {st['with_adapter']} with a bundled adapter.")


def cmd_services(args: argparse.Namespace) -> int:
    if args.category:
        try:
            cat = catalog.Category(args.category)
        except ValueError:
            valid = ", ".join(c.value for c in catalog.categories())
            print(f"Unknown category '{args.category}'. Valid: {valid}")
            return 2
        services = catalog.by_category(cat)
    elif args.search:
        services = catalog.search(args.search)
    else:
        services = list(catalog.all_services())
    _print_services(services)
    return 0


def cmd_service(args: argparse.Namespace) -> int:
    svc = catalog.get(args.id)
    if svc is None:
        print(f"No service '{args.id}'. Try `trade.py services --search {args.id}`.")
        return 2
    runnable, reason = (False, None)
    if svc.adapter:
        runnable, reason = registry.broker_availability(svc.adapter)
    print(f"{svc.name}  [{svc.id}]")
    print(f"  category     : {svc.category.value}")
    print(f"  asset classes: {', '.join(a.value for a in svc.assets) or '-'}")
    print(f"  apis         : {', '.join(svc.apis)}")
    print(f"  auth         : {svc.auth}")
    print(f"  capabilities : {', '.join(svc.capabilities) or '-'}")
    print(f"  adapter      : {svc.available_via}"
          + ("" if not svc.adapter else f"  ({'ready' if runnable else 'needs: ' + str(reason)})"))
    if svc.sdk:
        print(f"  sdk          : {svc.sdk}")
    if svc.docs:
        print(f"  docs         : {svc.docs}")
    if svc.notes:
        print(f"  notes        : {svc.notes}")
    return 0


def cmd_providers(args: argparse.Namespace) -> int:
    print("Broker adapters:")
    for adapter_id in registry.registered_broker_adapters():
        runnable, reason = registry.broker_availability(adapter_id)
        status = "ready" if runnable else f"unavailable ({reason})"
        venues = [s.id for s in catalog.all_services() if s.adapter == adapter_id]
        preview = ", ".join(venues[:8]) + (" ..." if len(venues) > 8 else "")
        print(f"  - {adapter_id:10s} {status}")
        if venues:
            print(f"      covers {len(venues)} catalog venue(s): {preview}")
    print("\nNotifier adapters:")
    for adapter_id in registry.registered_notifier_adapters():
        print(f"  - {adapter_id}")
    return 0


def _build_broker(provider: str):
    """Resolve a catalog id or adapter id to a constructed broker."""

    svc = catalog.get(provider)
    if svc is not None:
        if not svc.adapter:
            raise SystemExit(
                f"'{svc.name}' has no bundled adapter yet. Use --provider paper, "
                f"or a venue with an adapter (see `trade.py providers`)."
            )
        if svc.adapter == "ccxt":
            return registry.create_broker("ccxt", exchange_id=svc.id)
        return registry.create_broker(svc.adapter)
    return registry.create_broker(provider)


def cmd_quote(args: argparse.Namespace) -> int:
    broker = _build_broker(args.provider)
    quote = broker.get_quote(args.symbol)
    tag = " (paper)" if getattr(broker, "paper", False) else ""
    print(f"{quote.symbol}: {quote.price:,.2f}{tag}")
    return 0


def _place(args: argparse.Namespace, side: OrderSide) -> int:
    broker = _build_broker(args.provider)
    order = Order(
        symbol=args.symbol, side=side, type=OrderType.MARKET,
        quote_amount=args.amount, base_size=args.base_size,
    )
    if not getattr(broker, "paper", False) and not args.execute:
        quote = broker.get_quote(args.symbol)
        print(f"DRY RUN (add --execute to place): {side.value} {args.symbol} "
              f"for ${args.amount} at ~{quote.price:,.2f} on {args.provider}")
        return 0
    result = broker.place_order(order)
    print(f"{result.status.value.upper()}: {result.side.value} {result.symbol} "
          f"filled {result.filled_size} @ {result.avg_price:,.2f} "
          f"(fee {result.fee}, notional ${result.notional:,.2f}) via {result.provider}")
    if result.raw.get("reason"):
        print(f"  reason: {result.raw['reason']}")
    if getattr(broker, "paper", False):
        bals = ", ".join(f"{b.currency}={b.total}" for b in broker.get_balances())
        print(f"  paper balances: {bals}")
    return 0 if result.status.value in ("filled", "accepted", "simulated") else 1


def cmd_buy(args: argparse.Namespace) -> int:
    return _place(args, OrderSide.BUY)


def cmd_sell(args: argparse.Namespace) -> int:
    return _place(args, OrderSide.SELL)


def cmd_ask(args: argparse.Namespace) -> int:
    plan = parse(args.text)
    print(format_plan(plan))
    print("-" * 60)
    if not plan.is_actionable:
        return 2

    broker = None
    execute = False
    target = plan.provider_id if catalog.get(plan.provider_id) else plan.adapter
    try:
        broker = _build_broker(target)
    except (SystemExit, KeyError, RuntimeError, ValueError) as exc:
        print(f"Note: {exc}\nFalling back to the offline paper venue for a safe preview.")
        broker = registry.create_broker("paper")

    is_paper = getattr(broker, "paper", False)
    if is_paper:
        execute = True  # paper is always safe to run
    elif args.execute:
        execute = True

    results = execute_plan(plan, broker=broker, dry_run=not execute)
    label = "EXECUTED" if execute else "PREVIEW (dry run; add --execute for a real venue)"
    print(label + ":")
    for r in results:
        if r.status.value == "simulated":
            print(f"  would {r.side.value} {r.symbol} for ${r.raw['quote_amount']:,.2f} on {r.provider}")
        else:
            print(f"  {r.status.value.upper()} {r.side.value} {r.symbol} "
                  f"filled {r.filled_size} @ {r.avg_price:,.2f} via {r.provider}")
    if is_paper and hasattr(broker, "get_balances"):
        bals = ", ".join(f"{b.currency}={b.total}" for b in broker.get_balances())
        print(f"  paper balances: {bals}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="trade.py", description="Unified automated-trading CLI")
    sub = parser.add_subparsers(dest="command", required=True)

    p_services = sub.add_parser("services", help="Browse the catalog of services")
    p_services.add_argument("--category", help="Filter by category (see `services` output footer)")
    p_services.add_argument("--search", help="Free-text search across the catalog")
    p_services.set_defaults(func=cmd_services)

    p_service = sub.add_parser("service", help="Show details for one service")
    p_service.add_argument("id")
    p_service.set_defaults(func=cmd_service)

    p_providers = sub.add_parser("providers", help="List adapters and what is runnable now")
    p_providers.set_defaults(func=cmd_providers)

    p_quote = sub.add_parser("quote", help="Get a price quote")
    p_quote.add_argument("symbol")
    p_quote.add_argument("--provider", default="paper")
    p_quote.set_defaults(func=cmd_quote)

    for name, func, verb in (("buy", cmd_buy, "Buy"), ("sell", cmd_sell, "Sell")):
        p = sub.add_parser(name, help=f"{verb} a symbol")
        p.add_argument("--provider", default="paper")
        p.add_argument("--symbol", required=True)
        p.add_argument("--amount", type=float, default=None, help="Quote-currency amount (e.g. USD)")
        p.add_argument("--base-size", type=float, default=None, help="Base-asset size instead of amount")
        p.add_argument("--execute", action="store_true", help="Place for real (non-paper venues)")
        p.set_defaults(func=func)

    p_ask = sub.add_parser("ask", help="Describe what you want in plain English")
    p_ask.add_argument("text")
    p_ask.add_argument("--execute", action="store_true", help="Place for real (non-paper venues)")
    p_ask.set_defaults(func=cmd_ask)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())

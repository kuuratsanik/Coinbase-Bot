"""The catalog of services a user can pick from.

This is intentionally *data*, not code paths: a structured, queryable inventory
of trading venues, market-data providers, and notification channels spanning the
whole automated-trading landscape. The CLI renders it so a human can browse and
choose; the planner searches it so an AI request can resolve a venue by name.

The ``adapter`` field links an entry to a concrete implementation registered in
``src.trading.registry``:

* ``"paper"``    -> always-available offline simulation engine
* ``"ccxt"``     -> generic crypto adapter (pip install ccxt + API keys)
* ``"coinbase"`` -> native Coinbase Advanced Trade adapter (coinbase-advanced-py)
* ``None``       -> catalogued for discovery; adapter not yet bundled

Marking an entry with an adapter does not require that optional dependency to be
installed; the registry reports it as available only if the import succeeds.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional

from src.trading.models import AssetClass


class Category(str, Enum):
    CRYPTO_EXCHANGE = "crypto_exchange"
    CRYPTO_DERIVATIVES = "crypto_derivatives"
    CRYPTO_DEX = "crypto_dex"
    BROKER = "broker"
    FOREX_CFD = "forex_cfd"
    FUTURES = "futures"
    AGGREGATOR = "aggregator"
    FRAMEWORK = "framework"
    BOT_PLATFORM = "bot_platform"
    COPY_TRADING = "copy_trading"
    MARKET_DATA = "market_data"
    BROKER_INFRA = "broker_infra"
    NOTIFIER = "notifier"
    SCHEDULER = "scheduler"
    SECRETS = "secrets"


@dataclass(frozen=True)
class Service:
    id: str
    name: str
    category: Category
    assets: tuple[AssetClass, ...] = ()
    apis: tuple[str, ...] = ("rest",)
    auth: str = "api_key"
    capabilities: tuple[str, ...] = ()
    adapter: Optional[str] = None
    sdk: Optional[str] = None
    docs: Optional[str] = None
    notes: Optional[str] = None

    @property
    def available_via(self) -> str:
        return self.adapter or "catalog-only"


def _s(**kwargs) -> Service:
    return Service(**kwargs)


CRYPTO = (AssetClass.CRYPTO,)


# --- Crypto exchanges (spot); most are reachable through the generic ccxt adapter ---
_CRYPTO_EXCHANGES = [
    _s(id="coinbase", name="Coinbase Advanced Trade", category=Category.CRYPTO_EXCHANGE,
       assets=CRYPTO, apis=("rest", "websocket"), auth="jwt_cdp",
       capabilities=("spot", "data"), adapter="coinbase", sdk="coinbase-advanced-py",
       docs="https://docs.cdp.coinbase.com/advanced-trade/docs/welcome",
       notes="Successor to the retired Coinbase Pro API; CDP keys (Ed25519/ECDSA)."),
    _s(id="kraken", name="Kraken", category=Category.CRYPTO_EXCHANGE, assets=CRYPTO,
       apis=("rest", "websocket"), capabilities=("spot", "margin", "data"), adapter="ccxt",
       sdk="ccxt / python-kraken-sdk", docs="https://docs.kraken.com/"),
    _s(id="binance", name="Binance", category=Category.CRYPTO_EXCHANGE, assets=CRYPTO,
       apis=("rest", "websocket"), capabilities=("spot", "margin", "data"), adapter="ccxt",
       sdk="ccxt / python-binance", notes="Heavy regional restrictions; see Binance.US."),
    _s(id="binanceus", name="Binance.US", category=Category.CRYPTO_EXCHANGE, assets=CRYPTO,
       apis=("rest", "websocket"), capabilities=("spot", "data"), adapter="ccxt", sdk="ccxt"),
    _s(id="bybit", name="Bybit", category=Category.CRYPTO_EXCHANGE, assets=CRYPTO,
       apis=("rest", "websocket"), capabilities=("spot", "derivatives", "data"), adapter="ccxt",
       sdk="ccxt / pybit"),
    _s(id="okx", name="OKX", category=Category.CRYPTO_EXCHANGE, assets=CRYPTO,
       apis=("rest", "websocket"), capabilities=("spot", "derivatives", "data"), adapter="ccxt", sdk="ccxt"),
    _s(id="kucoin", name="KuCoin", category=Category.CRYPTO_EXCHANGE, assets=CRYPTO,
       apis=("rest", "websocket"), capabilities=("spot", "data"), adapter="ccxt", sdk="ccxt"),
    _s(id="gateio", name="Gate.io", category=Category.CRYPTO_EXCHANGE, assets=CRYPTO,
       capabilities=("spot", "data"), adapter="ccxt", sdk="ccxt"),
    _s(id="bitget", name="Bitget", category=Category.CRYPTO_EXCHANGE, assets=CRYPTO,
       capabilities=("spot", "derivatives", "data"), adapter="ccxt", sdk="ccxt"),
    _s(id="mexc", name="MEXC", category=Category.CRYPTO_EXCHANGE, assets=CRYPTO,
       capabilities=("spot", "data"), adapter="ccxt", sdk="ccxt"),
    _s(id="htx", name="HTX (Huobi)", category=Category.CRYPTO_EXCHANGE, assets=CRYPTO,
       capabilities=("spot", "data"), adapter="ccxt", sdk="ccxt"),
    _s(id="bitfinex", name="Bitfinex", category=Category.CRYPTO_EXCHANGE, assets=CRYPTO,
       capabilities=("spot", "margin", "data"), adapter="ccxt", sdk="ccxt"),
    _s(id="bitstamp", name="Bitstamp", category=Category.CRYPTO_EXCHANGE, assets=CRYPTO,
       capabilities=("spot", "data"), adapter="ccxt", sdk="ccxt"),
    _s(id="gemini", name="Gemini", category=Category.CRYPTO_EXCHANGE, assets=CRYPTO,
       apis=("rest", "websocket", "fix"), capabilities=("spot", "data"), adapter="ccxt", sdk="ccxt"),
    _s(id="cryptocom", name="Crypto.com Exchange", category=Category.CRYPTO_EXCHANGE, assets=CRYPTO,
       capabilities=("spot", "derivatives", "data"), adapter="ccxt", sdk="ccxt"),
    _s(id="upbit", name="Upbit", category=Category.CRYPTO_EXCHANGE, assets=CRYPTO,
       capabilities=("spot", "data"), adapter="ccxt", sdk="ccxt"),
    _s(id="bitso", name="Bitso", category=Category.CRYPTO_EXCHANGE, assets=CRYPTO,
       capabilities=("spot", "data"), adapter="ccxt", sdk="ccxt"),
    _s(id="luno", name="Luno", category=Category.CRYPTO_EXCHANGE, assets=CRYPTO,
       capabilities=("spot", "data"), adapter="ccxt", sdk="ccxt"),
    _s(id="bitvavo", name="Bitvavo", category=Category.CRYPTO_EXCHANGE, assets=CRYPTO,
       capabilities=("spot", "data"), adapter="ccxt", sdk="ccxt"),
    _s(id="bitpanda", name="Bitpanda Fusion", category=Category.CRYPTO_EXCHANGE, assets=CRYPTO,
       capabilities=("spot", "data"), adapter="ccxt", sdk="ccxt"),
    _s(id="woo", name="WOO X", category=Category.CRYPTO_EXCHANGE, assets=CRYPTO,
       capabilities=("spot", "derivatives", "data"), adapter="ccxt", sdk="ccxt"),
    _s(id="coincheck", name="Coincheck", category=Category.CRYPTO_EXCHANGE, assets=CRYPTO,
       capabilities=("spot", "data"), adapter="ccxt", sdk="ccxt"),
]

# --- Crypto derivatives venues ---
_CRYPTO_DERIVS = [
    _s(id="deribit", name="Deribit", category=Category.CRYPTO_DERIVATIVES, assets=CRYPTO,
       apis=("rest", "websocket"), capabilities=("options", "futures", "data"), adapter="ccxt",
       sdk="ccxt", notes="Reference venue for crypto options."),
    _s(id="bitmex", name="BitMEX", category=Category.CRYPTO_DERIVATIVES, assets=CRYPTO,
       capabilities=("derivatives", "data"), adapter="ccxt", sdk="ccxt"),
    _s(id="krakenfutures", name="Kraken Futures", category=Category.CRYPTO_DERIVATIVES, assets=CRYPTO,
       capabilities=("futures", "data"), adapter="ccxt", sdk="ccxt"),
    _s(id="binancefutures", name="Binance Futures", category=Category.CRYPTO_DERIVATIVES, assets=CRYPTO,
       capabilities=("futures", "data"), adapter="ccxt", sdk="ccxt"),
    _s(id="delta", name="Delta Exchange", category=Category.CRYPTO_DERIVATIVES, assets=CRYPTO,
       capabilities=("derivatives", "data"), adapter="ccxt", sdk="ccxt"),
]

# --- Crypto DEX / on-chain ---
_CRYPTO_DEX = [
    _s(id="hyperliquid", name="Hyperliquid", category=Category.CRYPTO_DEX, assets=CRYPTO,
       apis=("rest", "websocket"), auth="wallet", capabilities=("perps", "data"), adapter="ccxt",
       sdk="ccxt / hyperliquid-python-sdk", notes="On-chain perpetuals."),
    _s(id="dydx", name="dYdX", category=Category.CRYPTO_DEX, assets=CRYPTO, auth="wallet",
       capabilities=("perps", "data"), adapter=None, sdk="dydx-v4-client"),
    _s(id="gmx", name="GMX", category=Category.CRYPTO_DEX, assets=CRYPTO, auth="wallet",
       apis=("onchain",), capabilities=("perps",), adapter=None),
    _s(id="uniswap", name="Uniswap", category=Category.CRYPTO_DEX, assets=CRYPTO, auth="wallet",
       apis=("onchain",), capabilities=("swap",), adapter=None, sdk="web3.py"),
    _s(id="zerox", name="0x Swap API", category=Category.CRYPTO_DEX, assets=CRYPTO, auth="api_key",
       capabilities=("swap", "routing"), adapter=None, docs="https://0x.org/docs"),
    _s(id="oneinch", name="1inch API", category=Category.CRYPTO_DEX, assets=CRYPTO, auth="api_key",
       capabilities=("swap", "routing"), adapter=None),
    _s(id="jupiter", name="Jupiter (Solana)", category=Category.CRYPTO_DEX, assets=CRYPTO, auth="wallet",
       capabilities=("swap", "routing"), adapter=None),
    _s(id="cowswap", name="CoW Protocol", category=Category.CRYPTO_DEX, assets=CRYPTO, auth="wallet",
       capabilities=("swap",), adapter=None),
]

# --- Equities / options / multi-asset brokers ---
STOCK = (AssetClass.EQUITY, AssetClass.ETF)
_BROKERS = [
    _s(id="alpaca", name="Alpaca", category=Category.BROKER, assets=(AssetClass.EQUITY, AssetClass.ETF, AssetClass.OPTION, AssetClass.CRYPTO),
       apis=("rest", "websocket"), capabilities=("spot", "options", "paper", "data"), adapter=None,
       sdk="alpaca-py", docs="https://docs.alpaca.markets/", notes="Great sandbox/paper-trading API."),
    _s(id="ibkr", name="Interactive Brokers", category=Category.BROKER,
       assets=(AssetClass.EQUITY, AssetClass.OPTION, AssetClass.FUTURE, AssetClass.FOREX, AssetClass.BOND),
       apis=("rest", "fix"), capabilities=("spot", "options", "futures", "forex", "data"), adapter=None,
       sdk="ib_insync / ib_async", notes="Widest global asset coverage."),
    _s(id="tradier", name="Tradier", category=Category.BROKER, assets=(AssetClass.EQUITY, AssetClass.OPTION),
       capabilities=("spot", "options", "data"), adapter=None, sdk="REST"),
    _s(id="tastytrade", name="tastytrade", category=Category.BROKER, assets=(AssetClass.EQUITY, AssetClass.OPTION, AssetClass.FUTURE),
       capabilities=("options",), adapter=None),
    _s(id="schwab", name="Charles Schwab (ex-TD Ameritrade)", category=Category.BROKER, assets=STOCK,
       capabilities=("spot", "options", "data"), adapter=None, notes="Absorbed thinkorswim/TDA API."),
    _s(id="tradestation", name="TradeStation", category=Category.BROKER,
       assets=(AssetClass.EQUITY, AssetClass.OPTION, AssetClass.FUTURE), capabilities=("spot", "futures"), adapter=None),
    _s(id="robinhood", name="Robinhood", category=Category.BROKER, assets=(AssetClass.CRYPTO, AssetClass.EQUITY),
       capabilities=("spot",), adapter=None, notes="Official crypto trading API."),
    _s(id="webull", name="Webull", category=Category.BROKER, assets=STOCK, capabilities=("spot",), adapter=None),
    _s(id="etrade", name="E*TRADE", category=Category.BROKER, assets=STOCK, capabilities=("spot", "options"), adapter=None),
    _s(id="moomoo", name="Moomoo / Futu OpenAPI", category=Category.BROKER, assets=STOCK,
       capabilities=("spot", "options", "data"), adapter=None, sdk="futu-api"),
    _s(id="saxo", name="Saxo Bank OpenAPI", category=Category.BROKER,
       assets=(AssetClass.EQUITY, AssetClass.FOREX, AssetClass.CFD, AssetClass.FUTURE),
       capabilities=("spot", "forex", "cfd"), adapter=None),
    _s(id="questrade", name="Questrade", category=Category.BROKER, assets=STOCK, capabilities=("spot",), adapter=None),
    _s(id="snaptrade", name="SnapTrade (multi-broker)", category=Category.BROKER, assets=STOCK,
       capabilities=("spot", "aggregator"), adapter=None, notes="One API routing to many retail brokers."),
]

# --- Forex / CFD ---
FX = (AssetClass.FOREX, AssetClass.CFD)
_FOREX = [
    _s(id="oanda", name="OANDA", category=Category.FOREX_CFD, assets=FX, apis=("rest", "websocket"),
       capabilities=("forex", "cfd", "data", "paper"), adapter=None, sdk="oandapyV20",
       notes="Well-documented REST/streaming API with practice accounts."),
    _s(id="forexcom", name="FOREX.com / GAIN", category=Category.FOREX_CFD, assets=FX, capabilities=("forex", "cfd"), adapter=None),
    _s(id="ig", name="IG", category=Category.FOREX_CFD, assets=FX, capabilities=("forex", "cfd", "data"), adapter=None),
    _s(id="dukascopy", name="Dukascopy (JForex)", category=Category.FOREX_CFD, assets=FX, capabilities=("forex", "cfd", "data"), adapter=None),
    _s(id="mt5", name="MetaTrader 5", category=Category.FOREX_CFD, assets=FX, capabilities=("forex", "cfd"), adapter=None,
       sdk="MetaTrader5 (Python)", notes="Dominant retail FX/CFD automation stack; broker-provided."),
    _s(id="ctrader", name="cTrader Open API", category=Category.FOREX_CFD, assets=FX, capabilities=("forex", "cfd"), adapter=None),
    _s(id="pepperstone", name="Pepperstone", category=Category.FOREX_CFD, assets=FX, capabilities=("forex", "cfd"), adapter=None),
]

# --- Futures / institutional connectivity ---
_FUTURES = [
    _s(id="cme", name="CME Group", category=Category.FUTURES, assets=(AssetClass.FUTURE,), apis=("fix",),
       auth="fix", capabilities=("futures",), adapter=None, notes="Accessed via brokers/ISVs over FIX."),
    _s(id="ice", name="ICE", category=Category.FUTURES, assets=(AssetClass.FUTURE,), apis=("fix",), auth="fix",
       capabilities=("futures",), adapter=None),
    _s(id="rithmic", name="Rithmic API", category=Category.FUTURES, assets=(AssetClass.FUTURE,),
       capabilities=("futures", "data"), adapter=None),
    _s(id="cqg", name="CQG API", category=Category.FUTURES, assets=(AssetClass.FUTURE,),
       capabilities=("futures", "data"), adapter=None),
    _s(id="tt", name="Trading Technologies (TT API)", category=Category.FUTURES, assets=(AssetClass.FUTURE,),
       capabilities=("futures", "oms"), adapter=None),
]

# --- Aggregators / connectivity libraries ---
_AGGREGATORS = [
    _s(id="ccxt", name="ccxt", category=Category.AGGREGATOR, assets=CRYPTO, apis=("rest", "websocket"),
       auth="api_key", capabilities=("spot", "derivatives", "data"), adapter="ccxt", sdk="ccxt",
       docs="https://github.com/ccxt/ccxt", notes="One interface to 100+ crypto exchanges."),
    _s(id="hummingbot", name="Hummingbot", category=Category.AGGREGATOR, assets=CRYPTO,
       capabilities=("market_making", "arbitrage"), adapter=None),
    _s(id="cryptofeed", name="cryptofeed", category=Category.AGGREGATOR, assets=CRYPTO, apis=("websocket",),
       capabilities=("data",), adapter=None),
    _s(id="fix", name="FIX protocol (QuickFIX)", category=Category.AGGREGATOR, apis=("fix",), auth="fix",
       capabilities=("routing",), adapter=None, sdk="quickfix"),
]

# --- Backtesting / quant frameworks ---
_FRAMEWORKS = [
    _s(id="quantconnect", name="QuantConnect / LEAN", category=Category.FRAMEWORK,
       capabilities=("backtest", "live", "multi_broker"), adapter=None, docs="https://www.quantconnect.com/"),
    _s(id="nautilus", name="NautilusTrader", category=Category.FRAMEWORK,
       capabilities=("backtest", "live"), adapter=None, sdk="nautilus_trader"),
    _s(id="backtrader", name="Backtrader", category=Category.FRAMEWORK, capabilities=("backtest",), adapter=None),
    _s(id="vectorbt", name="vectorbt", category=Category.FRAMEWORK, capabilities=("backtest",), adapter=None),
    _s(id="freqtrade", name="Freqtrade", category=Category.FRAMEWORK, assets=CRYPTO,
       capabilities=("backtest", "live", "bot"), adapter=None),
    _s(id="jesse", name="Jesse", category=Category.FRAMEWORK, assets=CRYPTO, capabilities=("backtest", "live"), adapter=None),
]

# --- No-code / retail bot platforms ---
_BOTS = [
    _s(id="3commas", name="3Commas", category=Category.BOT_PLATFORM, assets=CRYPTO, capabilities=("bot", "copy"), adapter=None),
    _s(id="cryptohopper", name="Cryptohopper", category=Category.BOT_PLATFORM, assets=CRYPTO, capabilities=("bot",), adapter=None),
    _s(id="pionex", name="Pionex", category=Category.BOT_PLATFORM, assets=CRYPTO, capabilities=("bot",), adapter=None),
    _s(id="coinrule", name="Coinrule", category=Category.BOT_PLATFORM, assets=CRYPTO, capabilities=("bot",), adapter=None),
    _s(id="bitsgap", name="Bitsgap", category=Category.BOT_PLATFORM, assets=CRYPTO, capabilities=("bot",), adapter=None),
    _s(id="composer", name="Composer", category=Category.BOT_PLATFORM, assets=STOCK, capabilities=("bot", "no_code"), adapter=None),
    _s(id="tradetron", name="Tradetron", category=Category.BOT_PLATFORM, assets=STOCK, capabilities=("bot",), adapter=None),
]

# --- Copy / social trading ---
_COPY = [
    _s(id="etoro", name="eToro", category=Category.COPY_TRADING, assets=(AssetClass.EQUITY, AssetClass.CRYPTO), capabilities=("copy",), adapter=None),
    _s(id="zulutrade", name="ZuluTrade", category=Category.COPY_TRADING, assets=FX, capabilities=("copy",), adapter=None),
    _s(id="collective2", name="Collective2", category=Category.COPY_TRADING, assets=STOCK, capabilities=("copy", "signals"), adapter=None),
    _s(id="darwinex", name="Darwinex", category=Category.COPY_TRADING, assets=FX, capabilities=("copy",), adapter=None),
]

# --- Market data providers ---
_DATA = [
    _s(id="polygon", name="Polygon.io", category=Category.MARKET_DATA, assets=STOCK, apis=("rest", "websocket"),
       capabilities=("data",), adapter=None, docs="https://polygon.io/docs"),
    _s(id="databento", name="Databento", category=Category.MARKET_DATA, assets=STOCK, capabilities=("data",), adapter=None),
    _s(id="finnhub", name="Finnhub", category=Category.MARKET_DATA, assets=STOCK, capabilities=("data",), adapter=None),
    _s(id="alphavantage", name="Alpha Vantage", category=Category.MARKET_DATA, assets=STOCK, capabilities=("data",), adapter=None),
    _s(id="twelvedata", name="Twelve Data", category=Category.MARKET_DATA, assets=STOCK, capabilities=("data",), adapter=None),
    _s(id="tiingo", name="Tiingo", category=Category.MARKET_DATA, assets=STOCK, capabilities=("data",), adapter=None),
    _s(id="coingecko", name="CoinGecko", category=Category.MARKET_DATA, assets=CRYPTO, capabilities=("data",), adapter=None,
       auth="none", docs="https://www.coingecko.com/en/api"),
    _s(id="coinmarketcap", name="CoinMarketCap", category=Category.MARKET_DATA, assets=CRYPTO, capabilities=("data",), adapter=None),
    _s(id="kaiko", name="Kaiko", category=Category.MARKET_DATA, assets=CRYPTO, capabilities=("data",), adapter=None),
    _s(id="glassnode", name="Glassnode", category=Category.MARKET_DATA, assets=CRYPTO, capabilities=("onchain_data",), adapter=None),
    _s(id="fred", name="FRED (economic data)", category=Category.MARKET_DATA, capabilities=("macro_data",), adapter=None, auth="api_key"),
    _s(id="benzinga", name="Benzinga (news)", category=Category.MARKET_DATA, capabilities=("news",), adapter=None),
]

# --- Brokerage-as-a-service / infra ---
_INFRA = [
    _s(id="alpaca_broker", name="Alpaca Broker API", category=Category.BROKER_INFRA, assets=STOCK,
       capabilities=("embedded_brokerage",), adapter=None),
    _s(id="drivewealth", name="DriveWealth", category=Category.BROKER_INFRA, assets=STOCK, capabilities=("embedded_brokerage",), adapter=None),
    _s(id="apex", name="Apex Fintech", category=Category.BROKER_INFRA, assets=STOCK, capabilities=("clearing",), adapter=None),
    _s(id="zerohash", name="Zero Hash", category=Category.BROKER_INFRA, assets=CRYPTO, capabilities=("embedded_brokerage",), adapter=None),
    _s(id="fireblocks", name="Fireblocks", category=Category.BROKER_INFRA, assets=CRYPTO, capabilities=("custody", "execution"), adapter=None),
    _s(id="talos", name="Talos", category=Category.BROKER_INFRA, assets=CRYPTO, capabilities=("ems", "oms"), adapter=None),
]

# --- Notification channels ---
_NOTIFIERS = [
    _s(id="console", name="Console / stdout", category=Category.NOTIFIER, auth="none",
       capabilities=("notify",), adapter="console", notes="Always available; prints confirmations."),
    _s(id="webhook", name="Generic webhook", category=Category.NOTIFIER, auth="none",
       capabilities=("notify",), adapter="webhook", notes="POST JSON to any URL (Slack/Discord/Telegram/custom)."),
    _s(id="slack", name="Slack", category=Category.NOTIFIER, capabilities=("notify",), adapter="webhook",
       notes="Use an incoming-webhook URL with the webhook notifier."),
    _s(id="discord", name="Discord", category=Category.NOTIFIER, capabilities=("notify",), adapter="webhook"),
    _s(id="telegram", name="Telegram", category=Category.NOTIFIER, capabilities=("notify",), adapter="webhook"),
    _s(id="twilio", name="Twilio (SMS)", category=Category.NOTIFIER, capabilities=("notify",), adapter=None),
    _s(id="email_smtp", name="Email (SMTP)", category=Category.NOTIFIER, capabilities=("notify",), adapter=None,
       notes="Legacy channel carried over from the original bot."),
]

# --- Scheduling / secrets (supporting infra a user selects around execution) ---
_SCHED = [
    _s(id="apscheduler", name="APScheduler", category=Category.SCHEDULER, capabilities=("schedule",), adapter=None, auth="none"),
    _s(id="cron", name="cron / systemd timer", category=Category.SCHEDULER, capabilities=("schedule",), adapter=None, auth="none"),
    _s(id="eventbridge", name="AWS EventBridge Scheduler", category=Category.SCHEDULER, capabilities=("schedule",), adapter=None),
    _s(id="gha_cron", name="GitHub Actions cron", category=Category.SCHEDULER, capabilities=("schedule",), adapter=None, auth="none"),
]
_SECRETS = [
    _s(id="aws_secrets", name="AWS Secrets Manager", category=Category.SECRETS, capabilities=("secrets",), adapter=None),
    _s(id="vault", name="HashiCorp Vault", category=Category.SECRETS, capabilities=("secrets",), adapter=None),
    _s(id="doppler", name="Doppler", category=Category.SECRETS, capabilities=("secrets",), adapter=None),
    _s(id="dotenv", name=".env / python-dotenv", category=Category.SECRETS, capabilities=("secrets",), adapter=None, auth="none",
       notes="Local development secrets; used by the original bot."),
]

# The always-available simulation venue lives first so it is the obvious default.
_PAPER = [
    _s(id="paper", name="Paper trading (offline simulator)", category=Category.CRYPTO_EXCHANGE,
       assets=(AssetClass.CRYPTO, AssetClass.EQUITY, AssetClass.ETF), apis=("local",), auth="none",
       capabilities=("spot", "paper", "data"), adapter="paper", sdk="built-in",
       notes="Deterministic in-memory engine. No keys, no network, moves no real funds."),
]


CATALOG: tuple[Service, ...] = tuple(
    _PAPER
    + _CRYPTO_EXCHANGES
    + _CRYPTO_DERIVS
    + _CRYPTO_DEX
    + _BROKERS
    + _FOREX
    + _FUTURES
    + _AGGREGATORS
    + _FRAMEWORKS
    + _BOTS
    + _COPY
    + _DATA
    + _INFRA
    + _NOTIFIERS
    + _SCHED
    + _SECRETS
)

_BY_ID = {s.id: s for s in CATALOG}


def all_services() -> tuple[Service, ...]:
    return CATALOG


def get(service_id: str) -> Optional[Service]:
    return _BY_ID.get(service_id)


def categories() -> list[Category]:
    seen: list[Category] = []
    for s in CATALOG:
        if s.category not in seen:
            seen.append(s.category)
    return seen


def by_category(category: Category) -> list[Service]:
    return [s for s in CATALOG if s.category == category]


def search(query: str) -> list[Service]:
    q = (query or "").strip().lower()
    if not q:
        return list(CATALOG)
    results = []
    for s in CATALOG:
        haystack = " ".join(
            [s.id, s.name, s.category.value, s.auth, s.available_via]
            + list(s.capabilities)
            + [a.value for a in s.assets]
            + [s.sdk or "", s.notes or ""]
        ).lower()
        if q in haystack:
            results.append(s)
    return results


def stats() -> dict[str, int]:
    return {
        "total": len(CATALOG),
        "categories": len(categories()),
        "with_adapter": sum(1 for s in CATALOG if s.adapter),
    }

# Minimal, reproducible image for the trading toolkit.
# Uses uv for fast, deterministic dependency installation.
FROM python:3.13-slim

# uv: a fast Python package installer/resolver (https://docs.astral.sh/uv/).
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

WORKDIR /app

# Copy project sources. The core is standard-library only; optional venue
# integrations (ccxt, coinbase-advanced-py, alpaca) live in requirements-optional.txt.
COPY . .

# Core has no hard third-party runtime deps; install the ones the CLI/tests use.
RUN uv pip install --system --no-cache pyyaml python-dateutil python-dotenv requests

# Show the catalog by default; override with any `trade.py` subcommand, e.g.:
#   docker run --rm IMAGE python trade.py backtest --amount 100 --periods 52
CMD ["python", "trade.py", "services"]

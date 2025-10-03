# Coinbase Bot - AI Coding Agent Instructions

## Architecture Overview

This bot automates recurring cryptocurrency purchases on Coinbase Pro using a scheduled order execution system.

**Core Components:**
- **Input Layer** (`src/orders/`): Strategy pattern for collecting user inputs - `CommandLineInputCollector` for interactive CLI or `YAMLInputCollector` for config-driven batch orders
- **Validation Layer** (`src/orders/utilities.py`): `DataInputVerifier` validates dates (YYYY-MM-DD), times (HH:MM XM), frequencies, and dollar amounts
- **Authentication** (`src/coinbase/coinbase_bot.py`): `CoinbaseExchangeAuth` implements custom HMAC SHA256 signature authentication for Coinbase Pro API
- **Bot Logic** (`src/coinbase/coinbase_bot.py`): `CoinbaseBot` orchestrates scheduling and `CoinbaseProHandler` manages API interactions
- **Scheduling** (`src/coinbase/frequency.py`): Maps frequencies to timedeltas using `datetime` and `dateutil.relativedelta`

**Data Flow:** `place_order.py` → Input Collector → Validator → Bot (with Auth) → API Handler → Coinbase Pro API

## Critical Patterns

### Input Collection Strategy
```python
# CLI mode (default): Interactive validation loop
user_inputs = CommandLineInputCollector()

# YAML mode (--yaml flag): One-time validation with RuntimeError on failure
user_inputs = YAMLInputCollector()
```
Both inherit from `InputCollector` base class in `src/orders/input_collection.py`.

### Validation Loop Pattern
CLI collector repeatedly prompts until valid input:
```python
while not DataInputVerifier.is_valid_date_string(date_string):
    date_string = input("Enter valid date...")
```
YAML collector validates once and raises on invalid data.

### Credentials Management
Environment variables loaded from `.env` file (created by `initialize.sh`):
- `CB_API_KEY`, `CB_API_SECRET`, `CB_API_PASS` - Production API
- `CB_API_KEY_TEST`, `CB_API_SECRET_TEST`, `CB_API_PASS_TEST` - Sandbox API
- `EMAIL_ADDRESS`, `EMAIL_PASSWORD` - Email notifications

Accessed via `CoinbaseProCredentials()` and `CoinbaseSandboxCredentials()` in `src/coinbase/utilities.py`.

### Frequency Mapping
```python
FREQUENCY_TO_DAYS = {
    "daily": timedelta(days=1),
    "weekly": timedelta(days=7),
    "biweekly": timedelta(days=14),
    "monthly": relativedelta(months=1),  # Note: relativedelta for month-aware calculation
}
```

### Sandbox Mode Limitations
Two API methods are production-only (checks `"sandbox" not in self.coinbase.api_url`):
- `deposit_from_bank()` - Prints warning in sandbox
- `are_sufficient_funds_available()` - Prints warning in sandbox

Tests use `@pytest.mark.skipif(SANDBOX_CREDENTIALS.empty_credentials, ...)` to skip when no credentials.

## Development Workflow

### Initial Setup
```bash
sh initialize.sh  # Creates venv, installs deps, pre-commit hooks, generates .env
```

### Testing
All tests use **Coinbase Sandbox API** (`https://api-public.sandbox.pro.coinbase.com/`):
```bash
pytest                    # Run all tests
pytest tests/test_coinbase_bot.py  # Specific test file
```

Tests skip automatically if sandbox credentials missing. Configure in `initialize.sh` before running.

### Code Quality
Pre-commit hooks auto-format on commit:
- **Black** formatter (line-length: 120)
- **isort** with Black profile

Manual run: `pre-commit run --all-files`

## Integration Points

### Coinbase Pro API Endpoints
- `GET /payment-methods` - Retrieve bank account ID
- `POST /deposits/payment-method` - Deposit from bank
- `GET /accounts` - Check USD balance
- `POST /orders` - Place market order (product_id, funds)
- `GET /fills` - Retrieve transaction details

### Email Notifications
Uses Python `smtplib` to send order confirmations via user's email. Requires app password if 2FA enabled.

## Project Conventions

### File Structure
- `place_order.py` - Entry point
- `src/args/` - CLI argument parsing
- `src/orders/` - Input collection and validation
- `src/coinbase/` - API authentication, bot logic, handlers
- `tests/` - pytest suite with sandbox credentials

### Error Handling
- **CLI Mode**: Validation loops until valid input
- **YAML Mode**: Raises `RuntimeError` on invalid config
- **API Errors**: Raises `RuntimeError` with response content on non-200 status

### Threading in Tests
`test_activate()` uses threading with 150s timeout to test scheduled execution:
```python
thread_timeout_seconds = 150
# Sets next_deposit_date and next_purchase_date to current time + 1/2 minutes
```

### Date/Time Format Validation
- Date: `YYYY-MM-DD` validated with `datetime.strptime(date_string, "%Y-%m-%d")`
- Time: `HH:MM XM` validated with `datetime.strptime(time_string, "%I:%M %p")`
- Frequency: Must be in `["daily", "weekly", "biweekly", "monthly"]`

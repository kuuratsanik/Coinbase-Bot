# Coinbase Bot - AI Coding Instructions

## Architecture Overview

This is a cryptocurrency dollar-cost-averaging bot that automates recurring purchases on Coinbase Pro. The architecture follows a clean separation of concerns:

- **Entry Point**: `place_order.py` - main driver that orchestrates input collection, authentication, and bot activation
- **Input Collection**: Strategy pattern with `InputCollector` base class and two implementations:
  - `CommandLineInputCollector` - interactive CLI prompts with validation loops
  - `YAMLInputCollector` - batch processing from `orders.yaml` configuration
- **Core Bot Logic**: `CoinbaseBot` class handles scheduling, API authentication, fund deposits, and market orders
- **Validation**: Centralized in `DataInputVerifier` with comprehensive input validation for dates, times, crypto symbols, and amounts

## Key Patterns

### Input Validation Strategy
All user inputs go through strict validation in `src/orders/utilities.py`. The pattern is:
- CLI: Validation loops that re-prompt until valid input
- YAML: Immediate `RuntimeError` on invalid data
- Validation methods: `is_valid_date_string()`, `is_valid_time_string()`, `is_valid_crypto()`, etc.

### Credential Management
Environment variables loaded via `dotenv` in `src/coinbase/utilities.py`:
- Production: `CB_API_KEY`, `CB_API_SECRET`, `CB_API_PASS`  
- Testing: `CB_API_KEY_TEST`, `CB_API_SECRET_TEST`, `CB_API_PASS_TEST`
- Email: `EMAIL_ADDRESS`, `EMAIL_PASSWORD`

### API Authentication
Custom `CoinbaseExchangeAuth` class implementing Coinbase Pro's HMAC-SHA256 signature requirement. All API calls use this auth handler.

### Scheduling Pattern
Uses `threading.Timer` for recurring orders based on `FREQUENCY_TO_DAYS` mapping in `src/coinbase/frequency.py`. Supports daily, weekly, biweekly, and monthly frequencies.

## Development Workflows

### Setup
```bash
sh initialize.sh  # Creates venv, installs deps, sets up pre-commit hooks
# Then manually populate API credentials in initialize.sh before running
```

### Testing
- Tests use Coinbase Sandbox API with separate credentials
- Test files in `tests/files/` provide valid/invalid YAML examples
- Run with: `pytest -vv`
- Tests are skipped if sandbox credentials not provided

### Code Quality
- Black formatting (line-length: 120)
- isort import sorting (line-length: 120)  
- Pre-commit hooks enforce formatting

## Integration Points

### Coinbase Pro API
- Production: `https://api.pro.coinbase.com/`
- Sandbox: `https://api-public.sandbox.pro.coinbase.com/`
- Key endpoints: `/payment-methods`, `/deposits/payment-method`, `/orders`, `/fills`

### Email Notifications
Optional email confirmations via SMTP for successful orders. Uses standard `smtplib` with `EmailCredentials`.

## File Structure Conventions

- `src/coinbase/` - Core bot logic and API handling
- `src/orders/` - Input collection and validation
- `src/args/` - Command line argument parsing
- `tests/` - Unit tests with sandbox API integration
- `orders.yaml` - Configuration file for batch orders

## Error Handling

The codebase uses explicit error handling with detailed error messages:
- Type validation with `TypeError` for wrong parameter types
- Value validation with `ValueError` for invalid ranges/formats  
- API errors with `RuntimeError` containing response details
- All user-facing errors include "ERROR:" prefix for consistency
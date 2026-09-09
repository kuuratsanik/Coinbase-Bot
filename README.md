# Coinbase Bot

<h2> Description </h2>
This bot is used to set up recurring purchases on Coinbase Pro.
Coinbase Pro does not currently offer recurring purchases.
This provides a way to Dollar Cost Average into cyptocurrencies.


<h2> Configuration </h2>

You will need a Coinbase Pro account. You will also need to
create an API key via the Coinbase Pro website. Create your API key. 
Give the API key the View, Transfer, and Trade permissions. You will
also be given the following 3 pieces of information:

    key
    secret
    passphrase

Navigate to initialize.sh and populate the following variables:

    CB_API_KEY=""
    CB_API_SECRET=""
    CB_API_PASS=""

In order to run tests, you must also fill out the credentials for the Coinbase Sandbox
API:
                
    CB_API_KEY_TEST=""
    CB_API_SECRET_TEST=""
    CB_API_PASS_TEST=""

To receive email confirmations of successful orders, fill out the following as well:

    EMAIL_ADDRESS=""
    EMAIL_PASSWORD=""

You may need to adjust security settings on your email account for this to work properly.

After this is done, you can create a virtual environment, install dependencies, and create your .env file by running:

    sh initialize.sh


<h2> Usage </h2>

<h3>Input Orders via Command Line</h3>

Run the following command to start the program:

    python coinbase_bot.py

You will be prompted for the following:

    1. Enter in the start date in format YYYY-MM-DD:
    2. Enter in the time you wish to conduct transactions in format HH:MM XM:
    3. How often would you like to make purchases? Valid values include "daily", "weekly", "biweekly", and "monthly":
    4. Enter in the cryprocurrency symbol you wish to purchase:
    5. Enter in the amount in USD to purchase with: 10
    6. Do you wish to add more orders? Y/N
            a. If Y, then repeat steps 4 - 6
            b. If N, then program will continue

<h3>Input Orders via YAML</h3>

Navigate to the orders.yaml file where you will see the following sample order:

    crypto:
      - BTC
    start_date: 2025-01-01
    start_time: 07:00 AM
    frequency: weekly
    amount_usd:
      - 100

In here, you can input your recurring orders. Usage is as follows:

    crypto:
      - crypto_1
      - crypto_2
      ...
      - crypto_N
    start_date: YYYY-MM-DD
    start_time: HH:MM XM
    frequency: daily, weekly, biweekly, or monthly
    amount_usd:
      - amount_crypto_1
      - amount_crypto_2
      ...
      - amount_crypto_N

After setting this up, run this command to start the program:

    python coinbase_bot.py --yaml

<h3>What Happens?</h3>

The bot will first verify the values inputted are valid. For CLI, the program will
repeatedly ask you to input valid values if they are invalid. For YAML, a RuntimeError
will be thrown.

The bot then sums all values in the orders and deposits that amount into your Coinbase
Pro account. Each market order will be placed shortly after.

If you set up your email credentials correctly, you will be sent a confirmation once the
market order has been placed and filled. If you have 2FA enabled for your email, this may not work.


<h2> Multi-provider toolkit (pick a service, or ask AI) </h2>

The original bot targeted the Coinbase Pro API, which was retired in 2023. The
project now also ships a pluggable, provider-agnostic toolkit so you can pick any
service from a built-in catalog — or just describe what you want in plain English
and let the planner do it.

The core (service catalog, offline paper-trading engine, natural-language planner,
and CLI) uses only the Python standard library, so it runs with no credentials and
no extra installs. Real venues are optional adapters, loaded lazily:

    pip install -r requirements-optional.txt   # ccxt (~100 exchanges) + Coinbase Advanced Trade

Usage via the `trade.py` CLI:

    python trade.py services                      # browse the whole catalog
    python trade.py services --category crypto_exchange
    python trade.py services --search options     # free-text search
    python trade.py service coinbase              # details for one service
    python trade.py providers                     # which adapters are runnable now
    python trade.py quote --provider paper BTC-USD
    python trade.py buy --provider paper --symbol BTC-USD --amount 100
    python trade.py ask "DCA $50 of BTC and ETH weekly on coinbase"

The `paper` venue is the default and moves no real funds. Real venues place orders
only with `--execute` and valid credentials; an ambiguous natural-language request
is always shown as a reviewable plan and previewed on paper first.

Architecture (`src/trading/`):

- `models.py` / `base.py` — shared order/quote/balance types and adapter interfaces.
- `catalog.py` — the queryable inventory of exchanges, brokers, data, and notifiers.
- `registry.py` — maps a catalog entry to a concrete adapter; probes availability.
- `paper.py` — deterministic offline simulation engine (the always-available default).
- `ccxt_adapter.py` / `coinbase_adapter.py` — optional real-venue adapters.
- `notifiers.py` — pluggable console / webhook (Slack/Discord/Telegram) channels.
- `ai/planner.py` — plain-English → structured, reviewable trading plan.


<h2> Disclaimer </h2>
Any stock or ticker mentioned is not to be taken as financial advice. 

Real money is used, so proceed with caution.

You are using this bot at your own discretion and with the knowledge that you can lose (part of) your investment.
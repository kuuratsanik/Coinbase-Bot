import base64
import hashlib
import hmac
import json
import smtplib
from datetime import datetime, timedelta
from email.message import EmailMessage
from time import sleep, time

import requests
from requests.auth import AuthBase

from src.coinbase.frequency import FREQUENCY_TO_DAYS
from src.coinbase.utilities import EmailCredentials

COINBASE_API_URL = "https://api.pro.coinbase.com/"


# Create custom authentication for Exchange.
class CoinbaseExchangeAuth(AuthBase):
    def __init__(self, api_key, secret_key, passphrase):
        self.api_key = api_key
        self.secret_key = secret_key
        self.passphrase = passphrase

    def __call__(self, request):
        timestamp = str(time())
        message = timestamp + request.method + request.path_url + (request.body or "")
        hmac_key = base64.b64decode(self.secret_key)
        signature = hmac.new(hmac_key, message.encode(), hashlib.sha256)
        signature_b64 = base64.b64encode(signature.digest()).decode()

        request.headers.update(
            {
                "CB-ACCESS-SIGN": signature_b64,
                "CB-ACCESS-TIMESTAMP": timestamp,
                "CB-ACCESS-KEY": self.api_key,
                "CB-ACCESS-PASSPHRASE": self.passphrase,
                "Content-Type": "application/json",
            }
        )

        return request


# Create custom handler for placing orders
class CoinbaseProHandler:
    def __init__(self, api_url, auth):
        self.api_url = api_url
        self.auth = auth
        self.email = EmailCredentials()

    def get_payment_method(self):
        """
        Retrieves the user's bank from Coinbase Pro profile.

        :return: The user's bank ID as a string
        """

        response = requests.get(self.api_url + "payment-methods", auth=self.auth)

        if response.status_code != 200:
            raise RuntimeError(f"ERROR: Could not find payment method: {response.content}")

        print("SUCCESS: Retrieved payment method")

        return response.json()[0]["id"]

    def deposit_from_bank(self, amount):
        """
        Deposits USD from user's bank account into their USD Wallet on Coinbase Pro.

        :param amount: The amount of USD to deposit
        :return: True if deposit is successful
        """

        if not isinstance(amount, (int, float)):
            raise TypeError("ERROR: amount must be of type int or float")

        if amount <= 0:
            raise ValueError("ERROR: amount must be a positive number")

        deposit_request = {
            "amount": amount,
            "currency": "USD",
            "payment_method_id": self.get_payment_method(),
        }

        response = requests.post(
            self.api_url + "deposits/payment-method",
            data=json.dumps(deposit_request),
            auth=self.auth,
        )

        if response.status_code != 200:
            raise RuntimeError(f"ERROR: Could not make deposit to Coinbase Pro account: {response.content}")

        print(f"SUCCESS: Deposited ${amount:.2f} to Coinbase Pro account.")
        return True

    def are_sufficient_funds_available(self, amount):
        """
        Checks if the user has enough USD to place a market order.

        :param amount: The amount of USD to make a purchase with
        :return: True if user has enough USD for the order; False otherwise
        """

        if not isinstance(amount, (int, float)):
            raise TypeError("ERROR: amount must be of type int or float")

        if amount <= 0:
            raise ValueError("ERROR: amount must be a positive number")

        response = requests.get(self.api_url + "coinbase-accounts", auth=self.auth)

        if response.status_code != 200:
            raise RuntimeError("ERROR: are_sufficient_funds_available() reported a failure")

        coinbase_wallets = response.json()

        available_balance = 0.0

        for wallet in coinbase_wallets:
            if wallet["name"] == "Cash (USD)" and wallet["currency"] == "USD":
                available_balance = float(wallet["balance"])
                break

        return available_balance >= amount

    def place_market_order(self, product, amount):
        """
        Places a market order for specified product with a specified amount of USD.

        :param product: The cryptocurrency to purchase as a string
        :param amount: The amount of USD to make a purchase with
        :return: True if the market order is successfully executed
        """

        if not isinstance(product, str):
            raise TypeError("ERROR: product must be of type str")

        if not isinstance(amount, (int, float)):
            raise TypeError("ERROR: amount must be of type int or float")

        if not product:
            raise ValueError("ERROR: product cannot be null")

        if amount <= 0:
            raise ValueError("ERROR: amount must be a positive number")

        market_order = {
            "type": "market",
            "side": "buy",
            "product_id": product + "-USD",
            "funds": amount,
        }

        response = requests.post(self.api_url + "orders", data=json.dumps(market_order), auth=self.auth)

        if response.status_code != 200:
            raise RuntimeError(f"Could not place market order: {response.content}")

        print(f"SUCCESS: Made a market order for ${amount:.2f} of {product}")

        # Sleep for 15 seconds to ensure Coinbase API updates
        sleep(15)

        return True

    def get_transaction_details(self, product, start_date):
        """
        Retrieves the JSON response of the transaction details.

        :param product: The cryptocurrency to get transaction details of as a string
        :param start_date: String in "yyyy-mm-dd" format
        :return: Extracted details from the retrieved JSON as a dict
        """

        if not isinstance(product, str):
            raise TypeError("ERROR: product must be of type str")

        if not isinstance(start_date, str):
            raise TypeError("ERROR: start_date must be of type str")

        if not product:
            raise ValueError("ERROR: product cannot be null")

        if not start_date:
            raise ValueError("ERROR: start_date cannot be null")

        # Raises a ValueError if start_date is not in the right format
        datetime.strptime(start_date, "%Y-%m-%d")

        fill_parameters = {"product_id": product + "-USD", "start_date": start_date}

        response = requests.get(self.api_url + "fills", params=fill_parameters, auth=self.auth)

        if response.status_code != 200:
            raise RuntimeError("ERROR: Could not find transaction details")

        # Parse the JSON response
        transaction = response.json()[0]

        coinbase_fee = round(float(transaction["fee"]), 2)
        amount_invested = round(float(transaction["usd_volume"]), 2)
        purchase_price = round(float(transaction["price"]), 2)
        purchase_amount = transaction["size"]

        parsed_transaction = {
            "product": product,
            "start_date": start_date,
            "coinbase_fee": "%.2f" % coinbase_fee,
            "amount_invested": "%.2f" % amount_invested,
            "purchase_price": "%.2f" % purchase_price,
            "purchase_amount": purchase_amount,
            "total_amount": "%.2f" % (coinbase_fee + amount_invested),
        }

        return parsed_transaction

    def send_email_confirmation(self, transaction_details):
        """
        Sends user a confirmation email with the details of the transaction.

        :param transaction_details: Dict containing transaction details
        :return: True if the email is sent successfully; False otherwise
        """

        if not isinstance(transaction_details, dict):
            raise TypeError("ERROR: transaction_details must be of type dict")

        if not transaction_details:
            raise ValueError("ERROR: transaction_details cannot be null")

        product = transaction_details["product"]
        start_date = transaction_details["start_date"]
        coinbase_fee = transaction_details["coinbase_fee"]
        amount_invested = transaction_details["amount_invested"]
        purchase_price = transaction_details["purchase_price"]
        purchase_amount = transaction_details["purchase_amount"]
        total_amount = transaction_details["total_amount"]

        msg = EmailMessage()
        msg["Subject"] = f"Your Purchase of ${total_amount} of {product} Was Successful!"
        msg["From"] = self.email.email_address
        msg["To"] = self.email.email_address

        content = f"Hello,\n\n You successfully placed your order! Please see below details:\n\n \
            Amount Purchased: {purchase_amount} {product}\n \
            Purchase Price: ${purchase_price}\n \
            Total Amount: ${total_amount}\n \
            Amount Invested: ${amount_invested}\n \
            Coinbase Fees: ${coinbase_fee}\n \
            Date: {start_date}"

        msg.set_content(content)

        try:
            with smtplib.SMTP_SSL("smtp.gmail.com", 465) as smtp:
                smtp.login(self.email.email_address, self.email.password)
                smtp.send_message(msg)
                return True

        # It's okay if email doesn't work
        except smtplib.SMTPAuthenticationError:
            print("WARNING: Email credentials are not valid")

        return False


class CoinbaseBot:
    def __init__(self, api_url, auth, frequency, start_date, start_time, orders={}):
        self.coinbase = CoinbaseProHandler(api_url, auth)
        self.time_delta = FREQUENCY_TO_DAYS[frequency]
        self.next_purchase_date = self.parse_to_datetime(start_date, start_time)
        self.next_deposit_date = self.next_purchase_date + timedelta(minutes=-1)
        self.orders = orders

    def parse_to_datetime(self, date, time_):
        """
        Parses both a date string and a time string into one datetime object.

        :param date: The date string in format YYYY-MM-DD
        :param time_: The time string in format HH:MM XM
        :return: datetime object representing the passed in date and time strings
        """

        if not isinstance(date, str):
            raise TypeError("ERROR: date must be of type str")

        if not isinstance(time_, str):
            raise TypeError("ERROR: time_ must be of type str")

        if not date:
            raise ValueError("ERROR: date cannot be null")

        if not time_:
            raise ValueError("ERROR: time cannot be null")

        # Raises a ValueError is not in the correct formats
        datetime.strptime(date, "%Y-%m-%d")
        datetime.strptime(time_, "%I:%M %p")

        date_and_time = date + " " + time_
        date_and_time = datetime.strptime(date_and_time, "%Y-%m-%d %I:%M %p")

        return date_and_time

    def update_frequency(self, new_frequency):
        """
        Updates the frequency of the purchases.

        :param new_frequency: Valid values are "daily", "weekly", "biweekly", "monthly"
        :return: None
        """

        if not isinstance(new_frequency, str):
            raise TypeError("ERROR: new_frequency must be of type str")

        if new_frequency not in FREQUENCY_TO_DAYS:
            raise ValueError("ERROR: invalid value for new_frequency")

        self.time_delta = FREQUENCY_TO_DAYS[new_frequency]

    def update_deposit_date(self):
        """Updates to the next deposit date."""

        self.next_deposit_date += self.time_delta

    def update_purchase_date(self):
        """Updates to the next purchase date."""

        self.next_purchase_date += self.time_delta

    def is_time_to_deposit(self):
        """Returns True if the current datetime is the deposit datetime."""

        now = datetime.today().replace(second=0, microsecond=0)

        return now == self.next_deposit_date

    def is_time_to_purchase(self):
        """Returns True if current datetime is the purchase datetime."""

        now = datetime.today().replace(second=0, microsecond=0)

        return now == self.next_purchase_date

    def set_orders(self, **kwargs):
        """
        Sets the orders for recurring purchases.

        :param kwargs: Any number of key-value pairs for product to amount.
            Ex. {"BTC": 20, "ETH": 20, "ADA": 20}
        :return: None
        """

        if not isinstance(kwargs, dict):
            return TypeError("ERROR: kwargs must be of type dict")

        if not kwargs:
            return ValueError("ERROR: orders cannot be null")

        # Clear current orders dict
        self.orders = {}

        for product, amount in kwargs.items():
            self.orders[product] = amount

    def activate(self):
        """
        Activates the coinbase bot and performs transactions based on the dates and conditions.

        :return: None
        """

        print(f"Next deposit date: {self.next_deposit_date}")
        print(f"Next purchasing date: {self.next_purchase_date}")

        while True:
            # If our conditions are met, initiate transactions.
            if self.is_time_to_deposit():
                # Deposit from bank.
                deposit_amount = sum(self.orders.values())
                print(f"Depositing ${deposit_amount:.2f} into Coinbase Pro account. . .")

                # deposit_from_bank() not supported in sandbox mode
                if "sandbox" not in self.coinbase.api_url:
                    self.coinbase.deposit_from_bank(deposit_amount)
                else:
                    print("WARNING: deposit_from_bank() is not supported in sandbox mode")

                # Update to the next deposit date.
                self.update_deposit_date()

            if self.is_time_to_purchase():
                # Place market orders.
                for product, amount in self.orders.items():
                    print(f"Placing order for ${amount:.2f} of {product}. . .")

                    # are_sufficient_funds_available() not supported in sandbox mode
                    if "sandbox" not in self.coinbase.api_url:
                        if not self.coinbase.are_sufficient_funds_available(amount):
                            raise RuntimeError("User does not have sufficient funds for the current order")

                    else:
                        print("WARNING: are_sufficient_funds_available() not supported in sandbox mode")

                    self.coinbase.place_market_order(product, amount)

                    try:
                        purchase_date = self.next_purchase_date.strftime("%Y-%m-%d")
                        transaction_details = self.coinbase.get_transaction_details(product, purchase_date)
                        if self.coinbase.send_email_confirmation(transaction_details):
                            print("Email confirmation sent!")

                    # There are no transaction details
                    except IndexError:
                        print("ERROR: Email could not be sent.")

                # Update to the next purchase date.
                self.update_purchase_date()

                # Print out the next deposit/purchase dates.
                print(f"Next deposit date: {self.next_deposit_date}")
                print(f"Next purchasing date: {self.next_purchase_date}")

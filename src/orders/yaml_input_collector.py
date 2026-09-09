import os

import yaml

from src.orders.input_collection import InputCollector
from src.orders.utilities import DataInputVerifier

YAML_FILEPATH = os.getcwd() + "/orders.yaml"


class YAMLInputCollector(InputCollector):
    def __init__(self, yaml_filepath=YAML_FILEPATH, verbose=False):
        super().__init__()
        self.yaml_file = None
        self.load_yaml_file(yaml_filepath, verbose)

    def load_yaml_file(self, yaml_filepath=YAML_FILEPATH, verbose=False):
        """
        Loads the YAML file from the given filepath.

        :param yaml_filepath: Filepath to the YAML file
        :param verbose: True to print the loaded YAML file; False otherwise
        :return: None
        """

        with open(yaml_filepath) as yaml_file:
            self.yaml_file = yaml.load(yaml_file, Loader=yaml.BaseLoader)

        if verbose:
            print(self.yaml_file)

    def get_start_date(self):
        """Checks if the start date the user inputs is valid."""

        start_date = self.yaml_file["start_date"]

        if not DataInputVerifier.is_valid_date_string(start_date):
            raise RuntimeError(f"Date string '{start_date}' is not valid!")

        return start_date

    def get_start_time(self):
        """Checks if the start time the user inputs is valid."""

        start_time = self.yaml_file["start_time"]

        if not DataInputVerifier.is_valid_time_string(start_time):
            raise RuntimeError(f"Time string '{start_time}' is not valid!")

        return start_time

    def get_start_datetime(self):
        """Checks if the start date and time the user inputs is valid."""

        start_date = self.get_start_date()
        start_time = self.get_start_time()

        if not DataInputVerifier.is_valid_date_and_time_to_start(start_date, start_time):
            raise RuntimeError(f"Datetime string '{start_date} {start_time}' is not valid!")

        return start_date, start_time

    def get_frequency(self):
        """Checks if the frequency the user inputs is valid."""

        frequency = self.yaml_file["frequency"]

        if not DataInputVerifier.is_valid_frequency(frequency):
            raise RuntimeError(f"Frequency '{frequency}' is not valid!")

        return frequency

    def get_orders(self):
        """Constructs a dictionary of valid orders."""

        orders = {}
        crypto_list = self.yaml_file["crypto"]
        amount_usd_list = self.yaml_file["amount_usd"]

        if len(crypto_list) != len(amount_usd_list):
            raise RuntimeError("Number of crypto symbols does not match number of amounts given.")

        for crypto, dollar_amount in zip(crypto_list, amount_usd_list):
            if not DataInputVerifier.is_valid_crypto(crypto):
                raise RuntimeError(f"Cryptocurrency symbol '{crypto}' is not valid!")

            if not DataInputVerifier.is_valid_dollar_amount(dollar_amount):
                raise RuntimeError(f"Dollar amount '{dollar_amount}' is not valid!")

            orders[crypto] = dollar_amount

        return orders

    def collect_inputs(self):
        """Driver function to collect user inputs."""

        self.start_date, self.start_time = self.get_start_datetime()
        self.frequency = self.get_frequency()
        self.orders = self.get_orders()

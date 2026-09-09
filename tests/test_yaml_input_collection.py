import os
from datetime import datetime, timedelta

import pytest

from src.orders.yaml_input_collector import YAMLInputCollector

YAML_INVALID_ORDERS1 = os.getcwd() + "/tests/files/invalid_orders1.yaml"
YAML_INVALID_ORDERS2 = os.getcwd() + "/tests/files/invalid_orders2.yaml"
YAML_INVALID_ORDERS3 = os.getcwd() + "/tests/files/invalid_orders3.yaml"
YAML_INVALID_ORDERS4 = os.getcwd() + "/tests/files/invalid_orders4.yaml"
YAML_INVALID_ORDERS5 = os.getcwd() + "/tests/files/invalid_orders5.yaml"
YAML_INVALID_ORDERS6 = os.getcwd() + "/tests/files/invalid_orders6.yaml"
YAML_INVALID_ORDERS7 = os.getcwd() + "/tests/files/invalid_orders7.yaml"
YAML_VALID_ORDERS1 = os.getcwd() + "/tests/files/valid_orders1.yaml"
YAML_VALID_ORDERS2 = os.getcwd() + "/tests/files/valid_orders2.yaml"
YAML_VALID_ORDERS3 = os.getcwd() + "/tests/files/valid_orders3.yaml"
YAML_VALID_ORDERS4 = os.getcwd() + "/tests/files/valid_orders4.yaml"


class TestYAMLInputCollector:
    current_datetime = datetime.now()
    one_day_ago = (current_datetime + timedelta(days=-1)).strftime("%Y-%m-%d|%I:%M %p").split("|")
    one_day_later = (current_datetime + timedelta(days=1)).strftime("%Y-%m-%d|%I:%M %p").split("|")
    one_minute_later = (current_datetime + timedelta(minutes=1)).strftime("%Y-%m-%d|%I:%M %p").split("|")
    one_second_ago = (current_datetime - timedelta(seconds=1)).strftime("%Y-%m-%d|%I:%M %p").split("|")

    @pytest.mark.parametrize(
        "start_date,raises_error",
        [
            ("1", True),
            ("2021-02-29", True),
            ("2024/02/29", True),
            ("2024-02-29", False),
            ("2039-12-31", False),
        ],
    )
    def test_get_start_date(self, start_date, raises_error):
        """Tests YAMLInputCollector.get_start_date()."""

        input_collector = YAMLInputCollector(yaml_filepath=YAML_VALID_ORDERS1)
        input_collector.yaml_file["start_date"] = start_date

        if raises_error:
            with pytest.raises(RuntimeError, match=f"Date string '{start_date}' is not valid!"):
                input_collector.get_start_date()

        else:
            assert input_collector.get_start_date() == start_date

    @pytest.mark.parametrize(
        "start_time,raises_error",
        [
            ("1", True),
            ("10:00AM", True),
            ("7:0 PM", True),
            ("13:00 PM", True),
            ("12:61 PM", True),
            ("12:00 AM", False),
            ("12:00 PM", False),
        ],
    )
    def test_get_start_time(self, start_time, raises_error):
        """Tests YAMLInputCollector.get_start_time()."""

        input_collector = YAMLInputCollector(yaml_filepath=YAML_VALID_ORDERS1)
        input_collector.yaml_file["start_time"] = start_time

        if raises_error:
            with pytest.raises(RuntimeError, match=f"Time string '{start_time}' is not valid!"):
                input_collector.get_start_time()

        else:
            assert input_collector.get_start_time() == start_time

    @pytest.mark.parametrize(
        "start_date,start_time,raises_error",
        [
            (one_day_ago[0], one_day_ago[1], True),
            (one_second_ago[0], one_second_ago[1], True),
            (one_minute_later[0], one_minute_later[1], True),
            (one_day_later[0], one_day_later[1], False),
            ("2039-12-31", "10:00 AM", False),
        ],
    )
    def test_get_start_datetime(self, start_date, start_time, raises_error):
        """Tests YAMLInputCollector.get_start_datetime()."""

        input_collector = YAMLInputCollector(yaml_filepath=YAML_VALID_ORDERS1)
        input_collector.yaml_file["start_date"] = start_date
        input_collector.yaml_file["start_time"] = start_time

        if raises_error:
            with pytest.raises(RuntimeError, match=f"Datetime string '{start_date} {start_time}' is not valid!"):
                input_collector.get_start_datetime()

        else:
            assert input_collector.get_start_datetime() == (start_date, start_time)

    @pytest.mark.parametrize(
        "frequency,raises_error",
        [
            ("annually", True),
            ("semiannually", True),
            ("quarterly", True),
            ("daily", False),
            ("weekly", False),
            ("biweekly", False),
            ("monthly", False),
        ],
    )
    def test_get_frequency(self, frequency, raises_error):
        """Tests YAMLInputCollector.get_frequency()."""

        input_collector = YAMLInputCollector(yaml_filepath=YAML_VALID_ORDERS1)
        input_collector.yaml_file["frequency"] = frequency

        if raises_error:
            with pytest.raises(RuntimeError, match=f"Frequency '{frequency}' is not valid!"):
                input_collector.get_frequency()

        else:
            assert input_collector.get_frequency() == frequency

    @pytest.mark.parametrize(
        "crypto_list,amount_list,expected,raises_error,error_msg",
        [
            (["INVALID"], ["1000"], None, True, "Cryptocurrency symbol 'INVALID' is not valid!"),
            (["BTC"], ["One Hundred"], None, True, "Dollar amount 'One Hundred' is not valid!"),
            (["BTC"], ["-100"], None, True, "Dollar amount '-100' is not valid!"),
            (["BTC", "LINK"], ["1000"], None, True, "Number of crypto symbols does not match number of amounts given."),
            (["BTC"], ["1000"], {"BTC": "1000"}, False, None),
            (["BTC", "LINK"], ["500.50", "499.50"], {"BTC": "500.50", "LINK": "499.50"}, False, None),
        ],
    )
    def test_get_orders(self, crypto_list, amount_list, expected, raises_error, error_msg):
        """Tests YAMLInputCollector.get_orders()."""

        input_collector = YAMLInputCollector(yaml_filepath=YAML_VALID_ORDERS1)
        input_collector.yaml_file["crypto"] = crypto_list
        input_collector.yaml_file["amount_usd"] = amount_list

        if raises_error:
            with pytest.raises(RuntimeError, match=error_msg):
                input_collector.get_orders()

        else:
            assert input_collector.get_orders() == expected

    @pytest.mark.parametrize(
        "yaml_filepath,expected,raises_error,error_msg",
        [
            (YAML_INVALID_ORDERS1, None, True, "Cryptocurrency symbol 'INVALID' is not valid!"),
            (YAML_INVALID_ORDERS2, None, True, "Date string '2025/01/01' is not valid!"),
            (YAML_INVALID_ORDERS3, None, True, "Time string '07:60 AM' is not valid!"),
            (YAML_INVALID_ORDERS4, None, True, "Frequency 'quarterly' is not valid!"),
            (YAML_INVALID_ORDERS5, None, True, "Dollar amount 'One Hundred' is not valid!"),
            (YAML_INVALID_ORDERS6, None, True, "Number of crypto symbols does not match number of amounts given."),
            (YAML_INVALID_ORDERS7, None, True, "Datetime string '2023-01-01 07:00 AM' is not valid!"),
            (
                YAML_VALID_ORDERS1,
                {"start_date": "2099-01-01", "start_time": "12:00 AM", "frequency": "daily", "orders": {"BTC": "1000"}},
                False,
                None,
            ),
            (
                YAML_VALID_ORDERS2,
                {
                    "start_date": "2039-01-01",
                    "start_time": "11:59 PM",
                    "frequency": "weekly",
                    "orders": {"BTC": "150.55", "ETH": "149.45", "LINK": "50"},
                },
                False,
                None,
            ),
            (
                YAML_VALID_ORDERS3,
                {
                    "start_date": "2027-12-31",
                    "start_time": "3:32 AM",
                    "frequency": "biweekly",
                    "orders": {"BTC": "432.12", "ETH": "377.99", "LINK": "50"},
                },
                False,
                None,
            ),
            (
                YAML_VALID_ORDERS4,
                {
                    "start_date": "2032-02-29",
                    "start_time": "12:00 PM",
                    "frequency": "monthly",
                    "orders": {"BTC": "432.12", "ETH": "377.99", "LINK": "50"},
                },
                False,
                None,
            ),
        ],
    )
    def test_collect_inputs(self, yaml_filepath, expected, raises_error, error_msg):
        """Tests YAMLInputCollector.collect_inputs()."""

        input_collector = YAMLInputCollector(yaml_filepath=yaml_filepath, verbose=True)

        if raises_error:
            with pytest.raises(RuntimeError, match=error_msg):
                input_collector.collect_inputs()

        else:
            input_collector.collect_inputs()
            assert input_collector.start_date == expected["start_date"]
            assert input_collector.start_time == expected["start_time"]
            assert input_collector.frequency == expected["frequency"]
            assert input_collector.orders == expected["orders"]

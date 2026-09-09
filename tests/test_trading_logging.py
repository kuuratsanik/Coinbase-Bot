import json
import logging

from src.trading import logging_config
from src.trading.logging_config import JsonFormatter, configure_logging, get_logger, log_event


class TestJsonFormatter:
    def _record(self, **extra):
        record = logging.LogRecord(
            name="cbdca.test",
            level=logging.INFO,
            pathname=__file__,
            lineno=1,
            msg="hello",
            args=(),
            exc_info=None,
        )
        if extra:
            record.extra_fields = extra
        return record

    def test_emits_valid_json(self):
        out = JsonFormatter().format(self._record())
        payload = json.loads(out)
        assert payload["level"] == "INFO"
        assert payload["logger"] == "cbdca.test"
        assert payload["msg"] == "hello"

    def test_extra_fields_surface(self):
        out = JsonFormatter().format(self._record(symbol="BTC-USD", amount=50))
        payload = json.loads(out)
        assert payload["symbol"] == "BTC-USD"
        assert payload["amount"] == 50


class TestConfigureLogging:
    def test_idempotent_single_handler(self):
        configure_logging()
        configure_logging()
        root = logging.getLogger()
        assert len(root.handlers) == 1

    def test_json_format_selected(self):
        configure_logging(fmt="json")
        handler = logging.getLogger().handlers[0]
        assert isinstance(handler.formatter, JsonFormatter)
        configure_logging(fmt="text")  # reset for other tests

    def test_get_logger_configures(self):
        logging_config._CONFIGURED = False
        logger = get_logger("cbdca.x")
        assert logging_config._CONFIGURED is True
        assert logger.name == "cbdca.x"

    def test_log_event_does_not_raise(self, caplog):
        logger = get_logger("cbdca.event")
        with caplog.at_level(logging.INFO):
            log_event(logger, logging.INFO, "cycle_order", symbol="BTC-USD", amount=50)
        assert any(r.message == "cycle_order" for r in caplog.records)

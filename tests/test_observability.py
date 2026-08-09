import json
import logging

import pytest

from observability import JsonFormatter, start_metrics_if_configured


def test_json_formatter_contains_operational_metadata():
    record = logging.LogRecord(
        name="test",
        level=logging.INFO,
        pathname=__file__,
        lineno=1,
        msg="response delivered",
        args=(),
        exc_info=None,
    )
    payload = json.loads(JsonFormatter().format(record))
    assert payload["message"] == "response delivered"
    assert set(payload) >= {"timestamp", "level", "logger", "event_id"}


def test_metrics_server_is_disabled_by_default(monkeypatch):
    monkeypatch.delenv("METRICS_PORT", raising=False)
    assert start_metrics_if_configured() is None


@pytest.mark.parametrize("value", ["invalid", "0", "65536"])
def test_metrics_port_rejects_invalid_values(monkeypatch, value):
    monkeypatch.setenv("METRICS_PORT", value)
    with pytest.raises(RuntimeError, match="METRICS_PORT"):
        start_metrics_if_configured()

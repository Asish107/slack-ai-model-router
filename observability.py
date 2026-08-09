import contextvars
import json
import logging
import os
from datetime import datetime, timezone

from prometheus_client import Counter, Histogram, start_http_server


event_id_var = contextvars.ContextVar("event_id", default="-")

SLACK_EVENTS = Counter(
    "slack_router_events_total",
    "Slack mention events handled by outcome.",
    ("outcome",),
)
ROUTER_CALLS = Counter(
    "slack_router_api_calls_total",
    "Router API calls made by the Slack worker.",
    ("outcome", "tier", "category", "model", "fallback"),
)
ROUTER_LATENCY = Histogram(
    "slack_router_api_duration_seconds",
    "Latency of calls from Slack to the Router API.",
)


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "event_id": event_id_var.get(),
        }
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        return json.dumps(payload, default=str)


def configure_logging(level: str = "INFO") -> None:
    handler = logging.StreamHandler()
    handler.setFormatter(JsonFormatter())
    root = logging.getLogger()
    root.handlers.clear()
    root.addHandler(handler)
    root.setLevel(level.upper())


def start_metrics_if_configured() -> int | None:
    raw_port = os.environ.get("METRICS_PORT", "").strip()
    if not raw_port:
        return None
    try:
        port = int(raw_port)
    except ValueError as exc:
        raise RuntimeError("METRICS_PORT must be an integer.") from exc
    if not 1 <= port <= 65535:
        raise RuntimeError("METRICS_PORT must be between 1 and 65535.")
    start_http_server(port)
    return port

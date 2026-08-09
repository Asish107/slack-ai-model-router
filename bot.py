import asyncio
import logging
import os
import re
import time

from dotenv import load_dotenv
from slack_bolt.adapter.socket_mode.aiohttp import AsyncSocketModeHandler
from slack_bolt.async_app import AsyncApp
from observability import (
    ROUTER_CALLS,
    ROUTER_LATENCY,
    SLACK_EVENTS,
    configure_logging,
    event_id_var,
    start_metrics_if_configured,
)


load_dotenv()

from router_client import RouterClient  # noqa: E402


configure_logging(os.getenv("LOG_LEVEL", "INFO"))
logger = logging.getLogger(__name__)
MENTION_PATTERN = re.compile(r"<@[A-Z0-9]+>", re.IGNORECASE)
SLACK_MESSAGE_LIMIT = 3500


def clean_mention(text: str) -> str:
    return MENTION_PATTERN.sub("", text).strip()


def split_slack_message(text: str, limit: int = SLACK_MESSAGE_LIMIT) -> list[str]:
    """Split model output at natural boundaries below Slack's message limit."""
    remaining = text.strip()
    if not remaining:
        return ["(The model returned an empty response.)"]

    chunks: list[str] = []
    while len(remaining) > limit:
        split_at = remaining.rfind("\n", 0, limit + 1)
        if split_at < limit // 2:
            split_at = remaining.rfind(" ", 0, limit + 1)
        if split_at < limit // 2:
            split_at = limit
        chunks.append(remaining[:split_at].rstrip())
        remaining = remaining[split_at:].lstrip()
    if remaining:
        chunks.append(remaining)
    return chunks


def create_app(router_client: RouterClient) -> AsyncApp:
    app = AsyncApp(token=os.environ["SLACK_BOT_TOKEN"])

    @app.event("app_mention")
    async def handle_mention(event, say, client):
        event_token = event_id_var.set(str(event.get("event_ts") or event.get("ts") or "-"))
        if event.get("bot_id") or event.get("subtype") == "bot_message":
            event_id_var.reset(event_token)
            return

        prompt = clean_mention(event.get("text", ""))
        thread_ts = event.get("thread_ts", event["ts"])
        if not prompt:
            await say(text="What would you like help with?", thread_ts=thread_ts)
            SLACK_EVENTS.labels("empty_prompt").inc()
            event_id_var.reset(event_token)
            return

        pending = await say(text="Routing your request…", thread_ts=thread_ts)
        session_id = f"slack:{event['channel']}:{thread_ts}"
        route_started = time.perf_counter()
        try:
            result = await router_client.route(prompt, session_id)
            ROUTER_LATENCY.observe(time.perf_counter() - route_started)
            ROUTER_CALLS.labels(
                "success",
                result.tier,
                result.category,
                result.model,
                str(result.fallback_used).lower(),
            ).inc()
            fallback = " · fallback" if result.fallback_used else ""
            metadata = (
                f"_{result.tier} · {result.category} · "
                f"{result.model} · {result.latency_seconds:.2f} s{fallback}_"
            )
            response_chunks = split_slack_message(result.answer)
            if len(response_chunks[-1]) + len(metadata) + 2 <= SLACK_MESSAGE_LIMIT:
                response_chunks[-1] = f"{response_chunks[-1]}\n\n{metadata}"
            else:
                response_chunks.append(metadata)
        except Exception:
            ROUTER_LATENCY.observe(time.perf_counter() - route_started)
            ROUTER_CALLS.labels("error", "unknown", "unknown", "unknown", "false").inc()
            logger.exception("All model routes failed")
            response_chunks = ["Sorry, every configured model route failed. Try again."]

        try:
            await client.chat_update(
                channel=event["channel"], ts=pending["ts"], text=response_chunks[0]
            )
            for chunk in response_chunks[1:]:
                await say(text=chunk, thread_ts=thread_ts)
            SLACK_EVENTS.labels("delivered").inc()
            logger.info("slack_response_delivered chunks=%s", len(response_chunks))
        except Exception:
            SLACK_EVENTS.labels("delivery_error").inc()
            logger.exception("Slack response delivery failed")
            raise
        finally:
            event_id_var.reset(event_token)

    return app


async def main() -> None:
    metrics_port = start_metrics_if_configured()
    if metrics_port:
        logger.info("Prometheus metrics listening on port %s", metrics_port)
    router_client = RouterClient()
    app = create_app(router_client)
    handler = AsyncSocketModeHandler(app, os.environ["SLACK_APP_TOKEN"])
    try:
        health = await router_client.health()
        logger.info("Router API is healthy: %s", health.get("status"))
        await handler.start_async()
    finally:
        await handler.close_async()
        await router_client.close()


if __name__ == "__main__":
    asyncio.run(main())

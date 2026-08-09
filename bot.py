import asyncio
import logging
import os
import re

from dotenv import load_dotenv
from slack_bolt.adapter.socket_mode.aiohttp import AsyncSocketModeHandler
from slack_bolt.async_app import AsyncApp


load_dotenv()

from router_client import RouterClient  # noqa: E402


logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO"),
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
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
        if event.get("bot_id") or event.get("subtype") == "bot_message":
            return

        prompt = clean_mention(event.get("text", ""))
        thread_ts = event.get("thread_ts", event["ts"])
        if not prompt:
            await say(text="What would you like help with?", thread_ts=thread_ts)
            return

        pending = await say(text="Routing your request…", thread_ts=thread_ts)
        session_id = f"slack:{event['channel']}:{thread_ts}"
        try:
            result = await router_client.route(prompt, session_id)
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
            logger.exception("All model routes failed")
            response_chunks = ["Sorry, every configured model route failed. Try again."]

        await client.chat_update(
            channel=event["channel"], ts=pending["ts"], text=response_chunks[0]
        )
        for chunk in response_chunks[1:]:
            await say(text=chunk, thread_ts=thread_ts)

    return app


async def main() -> None:
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

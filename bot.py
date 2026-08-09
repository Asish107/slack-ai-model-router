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


def clean_mention(text: str) -> str:
    return MENTION_PATTERN.sub("", text).strip()


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
            response_text = f"{result.answer}\n\n{metadata}"
        except Exception:
            logger.exception("All model routes failed")
            response_text = "Sorry, every configured model route failed. Try again."

        await client.chat_update(
            channel=event["channel"], ts=pending["ts"], text=response_text
        )

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

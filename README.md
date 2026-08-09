# Slack AI Model Router

A standalone Slack assistant that classifies each channel mention and routes it
to an appropriate OpenRouter model tier. It does not depend on a separate web
service or model-router repository.

```text
Slack mention
    ↓
Local task classifier
    ↓
fast / mid / frontier / creative route
    ↓
OpenRouter model
    ↓
Threaded Slack answer + routing metadata
```

## Model routes

| Work | Default model |
| --- | --- |
| Simple Q&A, summaries, formatting | `~google/gemini-flash-latest` |
| Code, debugging, math, logic | `openai/gpt-5.6-terra` |
| Complex reasoning | `~openai/gpt-latest` |
| Creative and architecture | `anthropic/claude-sonnet-4.6` |

All model IDs can be overridden in `.env`.

## Features

- Slack Socket Mode: no public webhook or deployed web server required.
- Seven transparent task categories.
- Cost-aware routing for lightweight and difficult work.
- One fallback attempt through the fast route.
- Multi-turn memory scoped to each Slack thread.
- Immediate `Routing your request…` status message.
- Tier, category, model, latency, and fallback metadata.
- Async Slack and OpenRouter clients on one event loop.

## Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

Add your Slack and OpenRouter credentials to `.env`. Never commit that file.

Create or update the Slack app using [`slack-manifest.yaml`](slack-manifest.yaml).
It enables Socket Mode, subscribes to `app_mention`, and requests only
`app_mentions:read` and `chat:write` bot scopes. Create an app-level token with
`connections:write`, then install or reinstall the app to obtain the bot token.

## Run

```bash
python bot.py
```

Expected output:

```text
A new session has been established
⚡️ Bolt app is running!
```

Invite the app to a Slack channel and mention it using normal Slack text:

```text
@AI Model Router Analyze the trade-offs between queues and event streams.
```

Reply within the resulting thread to continue the same conversation.

## Tests

```bash
pip install -r requirements-dev.txt
pytest -q
```

Tests use fake clients and do not call Slack or OpenRouter.

## Scope

This is deliberately a Slack-only project. It has no FastAPI server, browser UI,
file-upload endpoint, or dependency on another repository. Potential next steps
include Slack file analysis, streaming replies, persistent Redis memory, request
deduplication, and per-user budgets.

## License

MIT

# Slack Client for Dynamic AI Model Router

A Slack Socket Mode client for the
[`Asish107/model-router`](https://github.com/Asish107/model-router) service.
Slack receives the mention and owns the user experience; the backend remains the
single source of truth for classification, model selection, OpenRouter access,
fallbacks, usage data, and conversation memory.

```text
Slack mention
    ↓
Slack worker
    ↓ HTTP POST /route
Model Router API
    ↓
OpenRouter model
    ↓
Threaded Slack answer + routing metadata
```

## Why it is separate

The Slack worker and Router API are independently deployable processes. This
keeps Slack credentials out of the web service and OpenRouter credentials out of
the Slack worker while ensuring every client uses the same routing policy.

The Slack project contains no model IDs, task classifier, OpenRouter SDK, or
session database.

## Local setup

Run the Router API first:

```bash
cd /path/to/model-router
source .venv/bin/activate
export OPENROUTER_API_KEY=sk-or-v1-your-key
uvicorn app:app --reload --port 8000
```

Then configure and run the Slack worker:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
python bot.py
```

Required Slack worker environment:

```dotenv
SLACK_BOT_TOKEN=xoxb-your-token
SLACK_APP_TOKEN=xapp-your-token
ROUTER_API_URL=http://127.0.0.1:8000
ROUTER_SERVICE_TOKEN=local-development-placeholder
ROUTER_TIMEOUT_SECONDS=120
```

The backend enforces `ROUTER_SERVICE_TOKEN` in production. Use the same secret
value in both services; never commit it to either repository.

## Observability

The worker emits structured JSON logs with a Slack event correlation ID. It
records Router API latency, result tier/category/model, fallback status, and Slack
delivery outcome. Message text, credentials, and service tokens are not
deliberately logged or used as metric labels.

Set `METRICS_PORT` to expose Prometheus metrics from the worker. Leave it empty
for local development when no metrics collector is running.

```dotenv
LOG_LEVEL=INFO
METRICS_PORT=9091
```

## Slack setup

Create or update the Slack app using [`slack-manifest.yaml`](slack-manifest.yaml).
Create an app-level token with `connections:write`, install the app, and invite it
to a channel.

Run:

```bash
python bot.py
```

Expected startup:

```text
Router API is healthy: healthy
A new session has been established
⚡️ Bolt app is running!
```

Mention the bot:

```text
@AI Model Router Analyze the trade-offs between queues and event streams.
```

The Slack thread ID becomes the backend `session_id`, so follow-up mentions in
the same thread share the backend's conversation memory.

## Tests

```bash
pip install -r requirements-dev.txt
pytest -q
```

Tests use an in-memory HTTP transport and do not call Slack, the Router API, or
OpenRouter.

## Production roadmap

- [x] Enforce service-token authentication on the Router API
- [ ] Add Redis queue and Slack `event_id` deduplication
- [ ] Move backend session memory to Redis
- [ ] Add per-workspace budgets and rate limits
- [x] Add structured logs and Prometheus metrics
- [x] Containerize API and Slack worker separately
- [ ] Export distributed traces to a monitoring backend
- [ ] Deploy API and Slack worker separately

## License

MIT

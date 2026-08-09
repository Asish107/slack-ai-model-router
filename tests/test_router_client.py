import asyncio

import httpx

from router_client import RouterClient


def test_route_maps_backend_contract():
    async def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/route"
        return httpx.Response(
            200,
            json={
                "response": "Paris",
                "category": "simple_qa",
                "tier": "fast",
                "model": "fast-model",
                "fallback_used": False,
                "latency_seconds": 0.42,
                "usage": {},
                "classification_reasoning": "simple question",
                "session_id": "slack:C1:123",
            },
        )

    async def run():
        transport = httpx.MockTransport(handler)
        http_client = httpx.AsyncClient(
            base_url="http://router.test", transport=transport
        )
        client = RouterClient(client=http_client)
        result = await client.route("Capital of France?", "slack:C1:123")
        await http_client.aclose()
        return result

    result = asyncio.run(run())
    assert result.answer == "Paris"
    assert result.tier == "fast"


def test_service_token_is_sent():
    async def handler(request: httpx.Request) -> httpx.Response:
        assert request.headers["Authorization"] == "Bearer secret"
        return httpx.Response(200, json={"status": "healthy"})

    async def run():
        transport = httpx.MockTransport(handler)
        http_client = httpx.AsyncClient(
            base_url="http://router.test",
            headers={"Authorization": "Bearer secret"},
            transport=transport,
        )
        client = RouterClient(client=http_client)
        result = await client.health()
        await http_client.aclose()
        return result

    assert asyncio.run(run())["status"] == "healthy"

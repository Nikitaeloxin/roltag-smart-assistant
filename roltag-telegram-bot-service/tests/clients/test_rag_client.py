import asyncio

import httpx
import pytest

from app.clients.rag_client import RagClient, RagClientError
from app.models.models import AskRequest


def _client(handler) -> RagClient:
    transport = httpx.MockTransport(handler)
    return RagClient(
        client=httpx.AsyncClient(transport=transport, base_url="http://rag.testing/api")
    )


def test_get_answer_returns_parsed_response():
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.headers["X-Request-ID"] == "req-1"
        return httpx.Response(
            200,
            json={
                "answer": "Replace the imaging oil every 6 months.",
                "sources": [{"document": "indigo_6600.pdf", "page": "42"}],
            },
        )

    response = asyncio.run(
        _client(handler).get_answer(AskRequest(question="q"), request_id="req-1")
    )

    assert response.answer == "Replace the imaging oil every 6 months."
    assert response.sources[0].document == "indigo_6600.pdf"


def test_get_answer_raises_rag_client_error_on_timeout():
    def handler(request: httpx.Request):
        raise httpx.TimeoutException("took too long")

    with pytest.raises(RagClientError):
        asyncio.run(
            _client(handler).get_answer(AskRequest(question="q"), request_id="req-1")
        )


def test_get_answer_raises_rag_client_error_on_upstream_error_status():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(502, json={"detail": "upstream down"})

    with pytest.raises(RagClientError):
        asyncio.run(
            _client(handler).get_answer(AskRequest(question="q"), request_id="req-1")
        )


def test_get_answer_raises_rag_client_error_on_invalid_response_body():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"unexpected": "shape"})

    with pytest.raises(RagClientError):
        asyncio.run(
            _client(handler).get_answer(AskRequest(question="q"), request_id="req-1")
        )

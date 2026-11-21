import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from pydantic import BaseModel

from app.core.errors import (
    UpstreamLLMError,
    UpstreamLLMTimeoutError,
    register_exception_handlers,
)


class _Body(BaseModel):
    question: str


@pytest.fixture()
def client():
    """A throwaway app wired only with the error handlers under test (from
    app/core/errors.py), plus a few routes that deliberately raise each
    error on purpose. Isolates the exception->response mapping logic from
    the real /api/ask route and its LLM/vectorstore dependencies."""
    app = FastAPI()
    register_exception_handlers(app)

    @app.get("/boom/upstream")
    def boom_upstream():
        raise UpstreamLLMError("LLM is down")

    @app.get("/boom/timeout")
    def boom_timeout():
        raise UpstreamLLMTimeoutError("LLM took too long")

    @app.get("/boom/unexpected")
    def boom_unexpected():
        raise ValueError("something broke")

    @app.post("/validate")
    def validate(body: _Body):
        return {"question": body.question}

    return TestClient(app, raise_server_exceptions=False)


def _assert_problem_shape(payload: dict, status: int, title: str, detail: str):
    assert payload["status"] == status
    assert payload["title"] == title
    assert payload["detail"] == detail
    assert payload["type"] == "about:blank"
    assert "instance" in payload


def test_upstream_llm_error_maps_to_502(client):
    response = client.get("/boom/upstream")
    assert response.status_code == 502
    _assert_problem_shape(
        response.json(), 502, "Assistant temporarily unavailable", "LLM is down"
    )


def test_upstream_llm_timeout_maps_to_504(client):
    response = client.get("/boom/timeout")
    assert response.status_code == 504
    _assert_problem_shape(
        response.json(), 504, "Assistant response timed out", "LLM took too long"
    )


def test_unexpected_exception_maps_to_500_without_leaking_details(client):
    response = client.get("/boom/unexpected")
    assert response.status_code == 500
    payload = response.json()
    _assert_problem_shape(
        payload, 500, "Internal Server Error", "An unexpected error occurred."
    )
    # the raw exception message must not leak to the client
    assert "something broke" not in response.text


def test_404_uses_problem_detail_shape(client):
    response = client.get("/does-not-exist")
    assert response.status_code == 404
    payload = response.json()
    assert payload["status"] == 404
    assert payload["type"] == "about:blank"


def test_validation_error_maps_to_422(client):
    response = client.post("/validate", json={})
    assert response.status_code == 422
    _assert_problem_shape(
        response.json(), 422, "Invalid request", "The request body failed validation."
    )

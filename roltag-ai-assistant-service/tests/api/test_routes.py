from unittest.mock import patch

from fastapi.testclient import TestClient

from app.core.errors import UpstreamLLMTimeoutError
from app.main import app
from app.models.models import AskResponse, Source

client = TestClient(app)


def test_ask_returns_answer_with_sources():
    # Patched where it's looked up (app.api.routes.answer_question), not where
    # it's defined (app.services.rag_service) -- routes.py already bound its
    # own reference to the function at import time, so patching the origin
    # module wouldn't affect what routes.py calls.
    fake_response = AskResponse(
        answer="Replace the imaging oil every 6 months.",
        sources=[Source(document="indigo_6600.pdf", page="42")],
    )
    with patch("app.api.routes.answer_question", return_value=fake_response) as mock_answer:
        response = client.post(
            "/api/ask", json={"question": "How often do I replace imaging oil?"}
        )

    assert response.status_code == 200
    body = response.json()
    assert body["answer"] == "Replace the imaging oil every 6 months."
    assert body["sources"] == [{"document": "indigo_6600.pdf", "page": "42"}]
    mock_answer.assert_called_once_with("How often do I replace imaging oil?")


def test_ask_requires_question_field():
    response = client.post("/api/ask", json={})
    assert response.status_code == 422
    assert response.json()["title"] == "Invalid request"


def test_ask_propagates_llm_timeout_as_504():
    # Mocks one level deeper, at app.services.rag_service.ask (the reference
    # rag_service.py bound when it did `from app.retrieval.retrieve import
    # ask`), so the real routes -> rag_service -> exception-handler chain
    # runs end to end without touching the real LLM/vectorstore.
    with patch(
        "app.services.rag_service.ask",
        side_effect=UpstreamLLMTimeoutError(
            "The assistant's language model took too long to respond."
        ),
    ):
        response = client.post(
            "/api/ask", json={"question": "How often do I replace imaging oil?"}
        )

    assert response.status_code == 504
    payload = response.json()
    assert payload["title"] == "Assistant response timed out"


def test_health_check():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "UP"}

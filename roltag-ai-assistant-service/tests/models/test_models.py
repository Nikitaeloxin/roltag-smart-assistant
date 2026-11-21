import pytest
from pydantic import ValidationError

from app.models.models import AskRequest, AskResponse, Source


def test_ask_request_requires_question():
    with pytest.raises(ValidationError):
        AskRequest()


def test_ask_request_accepts_question():
    request = AskRequest(question="How do I replace the imaging oil?")
    assert request.question == "How do I replace the imaging oil?"


def test_ask_response_defaults_to_empty_sources():
    response = AskResponse(answer="Some answer")
    assert response.sources == []


def test_ask_response_carries_sources():
    response = AskResponse(
        answer="Some answer",
        sources=[Source(document="manual.pdf", page="12")],
    )
    assert response.sources[0].document == "manual.pdf"
    assert response.sources[0].page == "12"


def test_source_fields_are_optional():
    source = Source(document=None, page=None)
    assert source.document is None
    assert source.page is None

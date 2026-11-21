
from app.models.models import AskResponse
from app.retrieval.retrieve import ask


def answer_question(question: str) -> AskResponse:
    return ask(question)
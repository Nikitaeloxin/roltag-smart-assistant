import logging

from fastapi import APIRouter

from app.models.models import AskRequest, AskResponse
from app.services.rag_service import answer_question

logger = logging.getLogger(__name__)

router = APIRouter()

@router.post("/ask", response_model=AskResponse)
async def ask(question: AskRequest) -> AskResponse:
    logger.info("received question", extra={"question": question.question})
    return answer_question(question.question)
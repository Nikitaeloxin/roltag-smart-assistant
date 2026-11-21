

import httpx
from pydantic_core import ValidationError

from app.models.models import AskRequest, AskResponse
from app.core.config import settings

class RagClientError(Exception):
    pass



class RagClient:
    def __init__(self, client: httpx.AsyncClient):
        self.client = client

    async def get_answer(self, question: AskRequest, request_id: str) -> AskResponse:
        try:
            response = await self.client.post(
                "/ask",
                json=question.model_dump(),
                headers={"X-Request-ID": request_id},
            )
            response.raise_for_status()
            return AskResponse.model_validate(response.json())
        except httpx.TimeoutException  as e:
            raise RagClientError("timeout") from e
        except httpx.HTTPStatusError as e:
            raise RagClientError(f"upstream status {e.response.status_code}") from e
        except (httpx.HTTPError, ValidationError) as e:
            raise RagClientError("upstream error") from e

rag_client = RagClient(
    client=httpx.AsyncClient(base_url=f"{settings.rag_base_url}/api", timeout=220.0)
)
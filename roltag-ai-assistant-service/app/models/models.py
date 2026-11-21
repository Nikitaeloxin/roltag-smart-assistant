from pydantic import BaseModel, Field

class AskRequest(BaseModel):
    question: str

class Source(BaseModel):
    document: str | None
    page: str | None

class AskResponse(BaseModel):
    answer: str
    sources: list[Source] = Field(default_factory=list)
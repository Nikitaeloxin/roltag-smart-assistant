import logging
from http import HTTPStatus

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.core.logging import request_id_var

logger = logging.getLogger(__name__)


class ProblemDetail(BaseModel):
    """RFC 9457 "Problem Details for HTTP APIs" response body."""

    type: str = "about:blank"
    title: str
    status: int
    detail: str
    instance: str


class AppError(Exception):

    status_code: int = 500
    title: str = "Internal Server Error"
    type_: str = "about:blank"

    def __init__(self, detail: str):
        super().__init__(detail)
        self.detail = detail


class UpstreamLLMError(AppError):
    status_code = 502
    title = "Assistant temporarily unavailable"


class UpstreamLLMTimeoutError(AppError):
    status_code = 504
    title = "Assistant response timed out"


def _problem_response(status: int, title: str, detail: str, type_: str = "about:blank") -> JSONResponse:
    problem = ProblemDetail(
        type=type_,
        title=title,
        status=status,
        detail=detail,
        instance=request_id_var.get(),
    )
    return JSONResponse(
        status_code=status,
        content=problem.model_dump(),
        media_type="application/problem+json",
    )


def register_exception_handlers(app: FastAPI) -> None:
    """Every error path returns the same RFC 9457 shape, instead of routes
    each inventing their own error body or everything collapsing into a
    bare 500."""

    @app.exception_handler(AppError)
    async def handle_app_error(request: Request, exc: AppError) -> JSONResponse:
        # Raised with `from e` at the call site, which already logged the
        # underlying cause with full context — nothing more to log here.
        return _problem_response(exc.status_code, exc.title, exc.detail, exc.type_)

    @app.exception_handler(RequestValidationError)
    async def handle_validation_error(request: Request, exc: RequestValidationError) -> JSONResponse:
        return _problem_response(
            422,
            "Invalid request",
            "The request body failed validation.",
        )

    @app.exception_handler(StarletteHTTPException)
    async def handle_http_exception(request: Request, exc: StarletteHTTPException) -> JSONResponse:
        return _problem_response(exc.status_code, HTTPStatus(exc.status_code).phrase, str(exc.detail))

    @app.exception_handler(Exception)
    async def handle_unexpected_error(request: Request, exc: Exception) -> JSONResponse:
        logger.exception("unhandled error")
        return _problem_response(500, "Internal Server Error", "An unexpected error occurred.")

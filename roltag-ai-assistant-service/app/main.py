import logging
import time

from fastapi import FastAPI, Request

from app.core.logging import new_request_id, request_id_var, setup_logging

setup_logging()

from app.api.routes import router
from app.core.errors import register_exception_handlers

logger = logging.getLogger("app.request")

app = FastAPI(
    title="Roltag AI assistant service",
    version="1.0.0",
)

register_exception_handlers(app)

#middleware to add request ID to each request and log the request details
@app.middleware("http")
async def add_request_id(request: Request, call_next):
    request_id = request.headers.get("X-Request-ID") or new_request_id()
    request_id_var.set(request_id)

    start = time.perf_counter()
    response = await call_next(request)

    response.headers["X-Request-ID"] = request_id
    logger.info(
        "request completed",
        extra={
            "method": request.method,
            "path": request.url.path,
            "status_code": response.status_code,
            "duration_ms": round((time.perf_counter() - start) * 1000, 1),
        },
    )
    return response


app.include_router(
    prefix="/api",
    router=router,
)

@app.get("/health")
async def health():
    return {"status": "UP"}

import contextvars
import json
import logging
import uuid

from app.core.config import settings

# Attributes always present on a stdlib LogRecord — anything else in
# record.__dict__ came from a logger.info(..., extra={...}) call and should
# be merged into the JSON payload.
_RESERVED_LOG_RECORD_ATTRS = {
    "name", "msg", "args", "levelname", "levelno", "pathname", "filename",
    "module", "exc_info", "exc_text", "stack_info", "lineno", "funcName",
    "created", "msecs", "relativeCreated", "thread", "threadName",
    "processName", "process", "message", "asctime", "taskName", "request_id",
}

# Correlates every log line emitted while handling one HTTP request (or one
# ask() call), across module boundaries (routes -> rag_service -> retrieve).
request_id_var: contextvars.ContextVar[str] = contextvars.ContextVar(
    "request_id", default="-"
)


def new_request_id() -> str:
    return uuid.uuid4().hex[:12]


class RequestIdFilter(logging.Filter):
    """Stamps the current request's correlation id onto every log record."""

    def filter(self, record: logging.LogRecord) -> bool:
        record.request_id = request_id_var.get()
        return True


class JsonFormatter(logging.Formatter):
    """One JSON object per line, so logs can be shipped to Loki/ELK/CloudWatch
    and filtered/aggregated by field instead of grepped as free text."""

    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "timestamp": self.formatTime(record, "%Y-%m-%dT%H:%M:%S%z"),
            "level": record.levelname,
            "logger": record.name,
            "request_id": getattr(record, "request_id", "-"),
            "message": record.getMessage(),
        }
        for key, value in record.__dict__.items():
            if key not in _RESERVED_LOG_RECORD_ATTRS and not key.startswith("_"):
                payload.setdefault(key, value)
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        return json.dumps(payload, default=str, ensure_ascii=False)


def setup_logging() -> None:
    """Call once at process startup. Level is controlled via LOG_LEVEL so ops
    can flip to DEBUG in production for full request/prompt tracing without
    a redeploy."""
    level = settings.log_level.upper()

    handler = logging.StreamHandler()
    handler.setFormatter(JsonFormatter())
    handler.addFilter(RequestIdFilter())

    root = logging.getLogger()
    root.handlers.clear()
    root.addHandler(handler)
    root.setLevel(level)

    # These are noisy at INFO/DEBUG and would drown out the RAG pipeline logs.
    libs_level = settings.log_level_libs.upper()
    for noisy_logger in ("httpx", "httpcore", "urllib3", "chromadb", "sentence_transformers"):
        logging.getLogger(noisy_logger).setLevel(libs_level)

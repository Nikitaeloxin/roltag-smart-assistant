# Roltag Telegram Bot Service

Thin proxy between a Telegram user and `roltag-ai-assistant-service`: receives the user's message over Telegram, forwards it as a question to the RAG service over HTTP, and sends the returned answer back in the chat. No RAG logic lives here.

## Status

Early-stage. **Done**: Telegram integration (aiogram), HTTP client for the RAG service, structured JSON logging with request-ID correlation, a typing indicator while the RAG call is in flight, and error handling around the upstream call — `RagClientError` in `rag_client.py` normalizes `httpx` timeout/status/validation failures; `echo_message_handler` catches it and replies with a generic "try again" message, and a `@dp.error()` global handler acts as a catch-all for anything else unhandled. **Not done**: auth/access control (anyone who finds the bot can use it), rate limiting, input validation beyond basic Pydantic typing.

## Tech stack

- Python 3.11 (pinned via `.python-version`), managed with `uv`
- **aiogram** (3.x) for the Telegram bot side
- **httpx** as the async HTTP client for `roltag-ai-assistant-service`
- `pydantic-settings` for config

## Architecture

```
main.py                  entry point; aiogram Bot/Dispatcher, command + message handlers,
                          _typing_loop (keeps the "typing..." indicator alive during a slow
                          RAG call), global_error_handler (catch-all fallback — see "Known gaps")
app/
  clients/rag_client.py  RagClient — POSTs AskRequest to RAG service's /api/ask; wraps httpx
                          timeout/status errors and response validation errors into RagClientError
  models/models.py       AskRequest / AskResponse / Source — mirrors the RAG service's API models
  core/
    config.py            Settings: telegram_bot_token, rag_base_url, log_level
    logging.py           JSON structured logging + request_id correlation (same pattern as
                          roltag-ai-assistant-service's app/core/logging.py)
Dockerfile                non-root user, uv-managed deps, runs `python main.py`
```

Each request gets a `request_id` (`new_request_id()` in `main.py`) that's attached to outgoing log lines and sent to the RAG service as the `X-Request-ID` header, so a single user question can be traced across both services' logs.

## Running

`.env`, `docker-compose.yml`, and `Makefile` live one level up in the `roltag/` repo root, not in this directory. From there:

```bash
make roltag-assistant   # builds + starts this service together with roltag-ai-assistant-service
```

Required env vars: `TELEGRAM_BOT_TOKEN`, `RAG_BASE_URL` (see `app/core/config.py`).

## Known gaps / things to watch for when working here

- No auth on the bot — no check restricts who can message it.

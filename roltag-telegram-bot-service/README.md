# Roltag Telegram Bot Service
## Description
The Telegram bot service is a thin proxy between a Telegram user and roltag-ai-assistant-service: it receives the user's message over Telegram, forwards it as a question to roltag-ai-assistant-service, and sends the returned answer back in the chat. It carries no RAG logic of its own. The project is written in **Python 3.11**, using the **aiogram** library for the Telegram side and **httpx** as the HTTP client for roltag-ai-assistant-service.

## Status
The service is at an early stage. **Done**: Telegram integration and HTTP integration with roltag-ai-assistant-service. **Not done**: security — no access control (anyone who finds the bot can use it), no rate limiting, no handling of a failed/slow upstream call, no input validation beyond basic typing.

## Architecture
### Internal services (main files)
- core
    - config.py - main settings for the app (external URLs, log levels, etc.)
    - logging.py - sets up the log format and adds a request_id to each log line
- clients
    - rag_client.py - client class responsible for REST API communication with roltag-ai-assistant-service
- models
    - models.py - describes the app's data models
- main.py - entry point for the service, implements the integration with Telegram

### External services
- roltag-ai-assistant-service - RAG service that answers questions

### Logging
Logs are formatted as JSON so they can be shipped to Loki (or another log collector), with the log level configurable through the env file. Each log record includes a `request_id` (read from the request headers, or generated if not present). (`/app/core/logging.py`)

## Prerequisites
- To run via Docker (recommended): **Docker** + **Docker Compose**, and `make`.
- To run locally without Docker: **Python 3.11** (pinned via `.python-version`) and **uv**.

## env
- TELEGRAM_BOT_TOKEN - security token received from Telegram
- RAG_BASE_URL - url of roltag-ai-assistant-service

## Setup
The `.env`, `docker-compose.yml` and `Makefile` live one level up, in the `roltag/` repo root (alongside this service's directory), not inside `roltag-telegram-bot-service/`.

1. From the `roltag/` root, make sure `.env` is filled in with `TELEGRAM_BOT_TOKEN` / `RAG_BASE_URL` (see "env" above) pointing at your running roltag-ai-assistant-service.

## How to run
### Via Makefile (recommended)
From the `roltag/` repo root (where `Makefile` and `docker-compose.yml` live):
```bash
make roltag-assistant # builds and starts the container (do it together with roltag-ai-assistant-service container,because roltag-telegram-bot-service depends on it)
```


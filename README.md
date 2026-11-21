# Roltag assistant

A RAG assistant for field technicians and operators maintaining **HP Indigo Digital Press** machines, exposed to users through a Telegram bot. Answers are grounded in the official technical documentation (manuals, service guides) and given in whichever language the question was asked in (English, Russian, or Hebrew).

## Services

- **roltag-ai-assistant-service** - the RAG service. REST API (`/api/ask`) that retrieves relevant manual chunks from ChromaDB and asks an LLM to answer. See its own [README](roltag-ai-assistant-service/README.md).
- **roltag-telegram-bot-service** - a thin Telegram bot that forwards user messages to roltag-ai-assistant-service and returns the answer. See its own [README](roltag-telegram-bot-service/README.md).
- **chromadb** - vector database server, holds the indexed manuals. Runs as its own Docker container.
- **Ollama** - serves the LLM (`qwen3:8b`). Not part of this repo - runs on a separate server, reached over HTTP.

## Tech stack
- **Python 3.11**, managed with **uv** (each service has its own `pyproject.toml`/`uv.lock`)
- **FastAPI** (RAG service's HTTP API) and **aiogram** (Telegram bot)
- **LangChain** for the RAG pipeline, **ChromaDB** as the vector store
- **Docker** + **Docker Compose** for running everything together

See each service's own README/CLAUDE.md for the full stack (embedding/reranker models, LLM, etc).

## Status
Early-stage, past the bare skeleton: retrieval, reranking, multilingual answers (EN/RU/HE),
structured logging, and RFC 9457 error responses work end-to-end in the RAG service; the
Telegram bot is a working thin proxy on top of it. Not yet done: authentication and rate
limiting on the RAG API, access control on the bot, and feeding eval results back into tuning.

## Repo structure
- `/roltag-ai-assistant-service` - the RAG service
- `/roltag-telegram-bot-service` - the Telegram bot
- `docker-compose.yml`, `Makefile`, `.env` - shared deployment config for all services (root level, not inside either service directory)

## Prerequisites
- An LLM reachable over HTTP (e.g. Ollama running `qwen3:8b`)
- **Docker** + **Docker Compose**, and `make`

## Setup
1. Fill in `.env` at the repo root:
   - `LLM_BASE_URL`, `LLM_MODEL_NAME` - your running LLM
   - `TELEGRAM_BOT_TOKEN` - bot token from Telegram
   - `LOG_LEVEL_LIBS` - optional, see roltag-ai-assistant-service's README
2. Index at least one manual so the assistant has something to retrieve from:
   ```bash
   make index   # indexes data/indigo_6600.pdf into ChromaDB (default)
   ```

## How to run
```bash
make roltag-assistant   # builds and starts chromadb, roltag-ai-assistant-service and roltag-telegram-bot-service
make down               # stop
make down-v             # stop and remove volumes (Chroma data, model cache)
```
The RAG API is available at `http://localhost:8001`, the Telegram bot connects to Telegram directly.

For running a single service locally without Docker, or more detail on either service, see its own README.

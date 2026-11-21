# Roltag

RAG assistant for HP Indigo Digital Press technicians, used through a Telegram bot. This is a monorepo of independent services, each with its own `CLAUDE.md` with service-specific detail.

## Services (sub-repos)

- `roltag-ai-assistant-service/` - the RAG API. Retrieval (ChromaDB + BAAI/bge-m3), reranking, LLM call (qwen3:8b via Ollama). See its [CLAUDE.md](roltag-ai-assistant-service/CLAUDE.md).
- `roltag-telegram-bot-service/` - thin Telegram-to-REST proxy, no RAG logic of its own. See its [CLAUDE.md](roltag-telegram-bot-service/CLAUDE.md).
- `chromadb` - vector store, runs as its own container (`chromadb/chroma` image), not part of either service's own code.
- LLM - external, not in this repo. Served separately via Ollama.

## Shared deployment files (repo root, not inside either service)

- `docker-compose.yml` - defines all containers: `chromadb`, `roltag-ai-assistant-service`, `roltag-telegram-bot-service`
- `Makefile` - `make index`, `make roltag-ai-assistant-service`, `make roltag-assistant`, `make down`, `make down-v`
- `.env` - env vars for all services (`LLM_BASE_URL`, `LLM_MODEL_NAME`, `LOG_LEVEL_LIBS`, `TELEGRAM_BOT_TOKEN`), gitignored

## Request flow

Telegram user -> `roltag-telegram-bot-service` -> `POST /api/ask` on `roltag-ai-assistant-service` -> similarity search + rerank against `chromadb` -> LLM (Ollama) -> answer + sources back through the chain.

## Working here

- Each service has its own `pyproject.toml`/`uv.lock`, Dockerfile, and tests - treat them as separate Python projects sharing one deployment config.
- When changing anything about ChromaDB, env vars, or how services talk to each other, check both root `docker-compose.yml` and the affected service's `CLAUDE.md`/README - they describe the same config from different angles and can drift out of sync.

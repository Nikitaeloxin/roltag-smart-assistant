# Roltag AI assistant service
## Description
RAG assistant for field technicians and operators maintaining **HP Indigo Digital Press** machines. It answers maintenance/operation questions grounded in the official technical documentation (manuals, service guides) for the relevant machine model, and replies in whichever language the question was asked in (English, Russian, or Hebrew). Project is written on **Python 3.11** using **FastApi** for client communication, **langchain** for rag settings, **ChromaDb** as avaectorstore, **qwen3:8b** as LLM.

## Status
Early-stage, past the bare skeleton: retrieval, reranking, multilingual answers, structured JSON logging with request-ID correlation, and RFC 9457 error responses are implemented and work end-to-end. **Not yet implemented**: authentication and rate limiting on `/api/ask`, and an eval-driven quality feedback loop (the eval harness itself exists — see "Evaluation results" below — but its results aren't yet fed back into tuning). Target deployment is an internal tool for a printing house with 1–50 concurrent users, not a public/multi-tenant service.

## Architecture
### Internal services (main files)
- core
    - config.py - main settings for the app (external URLs, log levels, etc.)
    - errors.py - defines exceptions (following RFC 9457 "Problem Details for HTTP APIs") and exception handling for FastAPI
    - logging.py - sets up the log format and adds a request_id to each log line
    - rag_config.py - a set of constants for the RAG setup, used across the app to configure RAG components
- api
    - routes.py - defines the FastAPI routes
- indexing
    - index.py - indexes PDF files
- models
    - models.py - describes the app's data models
- retrieval
    - retrieve.py - responsible for retrieving context and sending the request to the LLM
- services
    - rag_service.py - a service layer between FastAPI and the retrieval module
- main.py - entry point of the app; creates and configures FastAPI and logging

### External services
- ChromaDB - database where storing guide data in vector representation. Running as separated docker container
- LLM - runs locally (preferably on a separate machine), started separately. It formulates the answer to the question.
- roltag-telegram-bot - an app connected to Telegram, responsible for interacting with the client through Telegram. It talks to roltag-ai-assistant-service through its REST API.

## Repo structure
- /app - directory with the project's source code
- /data - directory that stores the base technical documents (manuals, service guides)
- /docs - contains project diagrams and ADR files
- /tests - the project's unit tests

## Architectural features
### Vectorstore, indexing
Text is split with **RecursiveCharacterTextSplitter** (from LangChain), using a chunk size of 1000 characters and an overlap of 200 characters. The vector store is **ChromaDB**, and the embedding model is **BAAI/bge-m3**. ChromaDB runs as its own server, reached over HTTP via `CHROMA_HOST`/`CHROMA_PORT`, with its data on a Docker volume (`chroma-data`).

### Retrieving, LLM
Before a question is sent to the LLM, it is augmented by a middleware (`AgentMiddleware` from `langchain.agents.middleware`) attached to the agent instance (created with `langchain.agents`). Retrieval uses `similarity_search` on ChromaDB with the same embedding model (**BAAI/bge-m3**). The LLM is **qwen3:8b**, running separately on another server and reached through HTTP requests from the agent.

### Error handling
A `ProblemDetail` class matches the response body defined by RFC 9457 ("Problem Details for HTTP APIs"). FastAPI's error handler returns `ProblemDetail` (or a class that inherits from it) to the client (`/app/core/errors.py`).

### Logging
Logs are formatted as JSON so they can be shipped to Loki (or another log collector), with the log level configurable through the env file. Each log record includes a `request_id` (read from the request headers, or generated if not present). (`/app/core/logging.py`)

### Evaluation results
`/app/eval/run_eval.py` is a script that evaluates this RAG app. `/app/eval/golden_qa_en.json` (and its Russian and Hebrew versions, `golden_qa_ru.json` and `golden_qa_he.json`, selected with `--lang`) contain 20 reference questions and answers. The script sends each question to the RAG pipeline and compares the reference (expected) answer with the actual answer. The output is a JSON file where each question gets a result object with the following fields:

- `id` - the question's ID in the golden Q&A file
- `question` - the question that was asked
- `category` - the question's category (e.g. `"maintenance"`, `"safety"`), from the golden Q&A file
- `expected_answer` - the reference (ground-truth) answer, from the golden Q&A file
- `actual_answer` - the answer that the RAG pipeline actually generated
- `expected_document` - the source document the reference answer should come from
- `expected_page` - the page of the source document the reference answer should come from
- `retrieved_hit` - `true` if the expected document/page was found among the retrieved chunks
- `retrieved_rank` - the rank of the expected chunk among the retrieved chunks (`1` is the best match), or `null` if it was not retrieved
- `cited_sources` - the document/page pairs that were actually used to build the answer
- `citation_hit` - `true` if the expected document/page is one of the `cited_sources`
- `keyword_recall` - a score from `0` to `1` for how many key words from `expected_answer` also appear in `actual_answer`
- `elapsed_ms` - how long the LLM call took, in milliseconds
- `error` - the error message if the call failed, otherwise `null`

Example:
```json
{
  "id": "q007",
  "question": "How frequently must HP Indigo ElectroInk Silver ink be rebuilt?",
  "category": "maintenance",
  "expected_answer": "Once a month, after the ink tank has been cleaned.",
  "actual_answer": "The ink must be rebuilt once a month, after the ink tank has been cleaned.",
  "expected_document": "indigo_6600.pdf",
  "expected_page": "2",
  "retrieved_hit": true,
  "retrieved_rank": 1,
  "cited_sources": [
    { "document": "data/indigo_6600.pdf", "page": "2" },
    { "document": "data/indigo_6600.pdf", "page": "1" },
    { "document": "data/indigo_6600.pdf", "page": "3" },
    { "document": "data/indigo_6600.pdf", "page": "21" },
    { "document": "data/indigo_6600.pdf", "page": "5" },
    { "document": "data/indigo_6600.pdf", "page": "25" }
  ],
  "citation_hit": true,
  "keyword_recall": 1.0,
  "elapsed_ms": 72824.5,
  "error": null
}
```

## Prerequisites
- An LLM reachable over HTTP, served separately (e.g. Ollama running `qwen3:8b`) — roltag-ai-assistant-service does not run the LLM itself, only calls it.
- To run via Docker (recommended): **Docker** + **Docker Compose**, and `make`.
- To run locally without Docker: **Python 3.11** (pinned via `.python-version`) and **uv**.

## env
- LLM_BASE_URL - url of running LLM
- LLM_MODEL_NAME - LLM model name
- LOG_LEVEL_LIBS - log level for noisy third-party libraries (`httpx`, `httpcore`, `urllib3`, `chromadb`, `sentence_transformers`), kept separate from the app's own log level so they don't drown it out. Default `WARNING`.
- CHROMA_HOST - hostname of the ChromaDB server. Default `localhost`; set to `chromadb` by `docker-compose.yml` so the app can reach the ChromaDB container by its service name.
- CHROMA_PORT - port of the ChromaDB server. Default `8000`.

## Setup
The `.env`, `docker-compose.yml` and `Makefile` live one level up, in the `roltag/` repo root (alongside this service's directory), not inside `roltag-ai-assistant-service/`.

1. From the `roltag/` root, make sure `.env` is filled in with `LLM_BASE_URL` / `LLM_MODEL_NAME` (see "env" above) pointing at your running LLM.
2. Index at least one manual into the vector store, otherwise `/api/ask` has nothing to retrieve from:

   Via Docker (recommended), from the `roltag/` repo root:
   ```bash
   make index                              # indexes data/indigo_6600.pdf (default)
   make index FILE=some_other_manual.pdf   # indexes a different file from roltag-ai-assistant-service/data
   make index ARGS=--replace               # wipes the collection first, then indexes
   ```
   This runs the indexer as a one-off container (`docker compose run --rm`), reusing the same image and HF model cache as the app container and writing to the same ChromaDB server, so the result is immediately picked up by `/api/ask`.

   Locally, without Docker:
   ```bash
   cd roltag-ai-assistant-service
   uv run python -m app.indexing.index --file data/indigo_6600.pdf
   ```
   This needs a ChromaDB server reachable at `CHROMA_HOST`/`CHROMA_PORT` (default `localhost:8000`) — e.g. `docker run -p 8000:8000 chromadb/chroma`, or the `chromadb` service from `docker-compose.yml` on its own (`docker compose up -d chromadb`).

## How to run
### Via Docker (recommended)
From the `roltag/` repo root (where `Makefile` and `docker-compose.yml` live):
```bash
make index                         # index a manual into the vector store (see "Setup" above)
make roltag-ai-assistant-service   # builds and starts the container
make down                          # stop
make down-v                        # stop and also remove volumes (Chroma data, model cache)
```
The API is then available at `http://localhost:8001`.

### Locally, without Docker (dev)
```bash
cd roltag-ai-assistant-service
uv sync
uv run uvicorn app.main:app --reload --port 8001
```
`LLM_BASE_URL` / `LLM_MODEL_NAME` must be available as environment variables or in a `.env` file inside `roltag-ai-assistant-service/` — the root `.env` is only picked up by `docker-compose`. A ChromaDB server must also be reachable at `CHROMA_HOST`/`CHROMA_PORT` (see "Setup" above).

## Smoke test
Once the service is running (either way above), send a question to it:
```bash
curl -X POST http://localhost:8001/api/ask \
  -H "Content-Type: application/json" \
  -d '{"question": "How frequently must HP Indigo ElectroInk Silver ink be rebuilt?"}'
```
A healthy response is an `AskResponse` JSON body with an `answer` and its supporting `sources` (document + page).
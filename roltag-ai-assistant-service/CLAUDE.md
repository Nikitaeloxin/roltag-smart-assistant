# Roltag AI Assistant Service

RAG assistant for field technicians and operators maintaining **HP Indigo Digital Press** machines (models include 6800, 6r, 8000, ...). It answers maintenance/operation questions grounded in the official technical documentation (manuals, service guides) for the relevant machine model.

## Status

Early-stage but past the bare skeleton: retrieval, reranking, multilingual answers, centralized config, structured logging, request-ID correlation, and RFC 9457 error responses are implemented. Auth, rate limiting, and the eval-driven quality loop are still open — check the actual code before assuming anything not listed here is done.

## Domain requirements

- **Answers must be grounded** in the technical documentation only. Rather than having the LLM generate an inline citation (unreliable/hallucination-prone on a small quantized model), each answer is returned with the source chunks it was generated from attached as structured metadata (document name, page number) — not asking the model to state where it got the answer. `app/indexing/index.py` stores `page_number` and `source` in chunk metadata; `ask()` in `app/retrieval/retrieve.py` surfaces this as `AskResponse.sources`, built deterministically from the reranked chunks (`RERANK_TOP_N`, currently 4) actually fed to the LLM.
- **Multilingual**: the assistant replies in the same language the user asked in. Confirmed required languages: English (default), Russian, Hebrew. `app/retrieval/language.py` detects the question's language via `langdetect` and falls back to English for anything outside the supported set; `RetrieveDocumentsMiddleware` in `app/retrieval/retrieve.py` appends an explicit "answer in {language}" instruction to the prompt.
  - Open concern: the small instruct model may not be strong enough for Hebrew/Russian generation quality — flagged for future evaluation, not yet resolved.
- **Documentation corpus**: currently one publicly available manual is indexed (`data/indigo_6600.pdf`) into the `hp_indigo_manual` Chroma collection via `app/indexing/index.py`. A second PDF (`data/954730512-CA339-10220-On-Site-Production-Support-6800.pdf`) is present in `data/` but **not yet indexed**. More model-specific manuals will be added later — expect the indexing/collection design to need to handle multiple machine models distinctly (metadata filtering by model, not just one flat collection).

## Tech stack

- Python >=3.10 (pinned to 3.11 via `.python-version`), managed with `uv` (`pyproject.toml` / `uv.lock`)
- **LangChain** (`langchain`, `langchain-chroma`, `langchain-huggingface`, `langchain-ollama`, `langchain-openai`, `langchain-text-splitters`) — the agent/middleware pipeline in `app/retrieval/retrieve.py` is built on `langchain.agents.create_agent`
- **FastAPI** + `uvicorn` for the HTTP API
- **ChromaDB** as the vector store (`langchain-chroma`), running as its own server (a separate Docker container), reached over HTTP via `CHROMA_HOST`/`CHROMA_PORT` (`app/core/config.py`)
- **Embeddings**: `BAAI/bge-m3` via `HuggingFaceEmbeddings`
- **Reranker**: `BAAI/bge-reranker-v2-m3` via `sentence-transformers`'s `CrossEncoder`, applied as a second-stage rerank over the Chroma similarity-search candidates
- **LLM**: served by a remote Ollama instance (model name and base URL configurable via `LLM_MODEL_NAME` / `LLM_BASE_URL` env vars, see `app/core/config.py`), accessed through `ChatOpenAI`'s OpenAI-compatible client
- **Language detection**: `langdetect`, used to pick the answer language (English/Russian/Hebrew, see "Multilingual" above)
- `pydantic-settings` for centralized config (`app/core/config.py`)
- `torch` (CPU-only wheel — no GPU in dev or target deployment), `transformers`, `sentence-transformers` as embedding/reranker-model dependencies
- `pytest` for the test suite (`tests/`)

## Architecture

```
app/
  main.py              FastAPI app; request-ID middleware; mounts router at /api, /health check
  api/routes.py         POST /api/ask -> AskRequest{question} -> answer_question()
  models/models.py      Pydantic request/response models (AskRequest, AskResponse, Source)
  services/rag_service.py   thin wrapper calling retrieval.ask()
  retrieval/
    retrieve.py          LangChain agent + RetrieveDocumentsMiddleware: similarity search against
                          Chroma (RETRIEVAL_CANDIDATE_K candidates), cross-encoder rerank
                          (BAAI/bge-reranker-v2-m3, RERANK_TOP_N kept), stuffs reranked chunk text
                          into the user message with a language instruction, calls the LLM via
                          ChatOpenAI pointed at a remote Ollama OpenAI-compatible endpoint
    language.py          langdetect-based language detection -> English/Russian/Hebrew, defaults to English
    llm_timing_callback.py  LangChain callback that measures LLM call latency for logging
  indexing/index.py     PDF loading (pypdf), token-aware chunking (RecursiveCharacterTextSplitter
                         sized against the bge-m3 tokenizer), embeddings (HuggingFaceEmbeddings
                         BAAI/bge-m3), Chroma vector store setup. __main__ CLI for ingestion (--file, --add/--replace)
  core/
    config.py            pydantic-settings Settings (env_file=".env"): chroma_host, chroma_port,
                          llm_base_url, llm_model_name, log_level, log_level_libs
    logging.py            JSON structured logging + request-ID correlation (see "Structural features" below)
    errors.py             RFC 9457 problem-details exception handlers (see "Structural features" below)
  eval/                  golden_qa_en.json / golden_qa_ru.json / golden_qa_he.json + run_eval.py (see "Running
                         the eval harness"); results/ holds output JSON
data/                    source PDFs (manuals)
tests/                   pytest suite: api/, core/, models/, retrieval/
Dockerfile               builds the app image (non-root user, uv-managed deps, runs uvicorn)
docker-compose.yml       runs the app container alongside a separate chromadb container; HF model
                         cache and Chroma data each on their own volume
```

## Structural features

### Logging

Configured once at startup by `setup_logging()` in `app/core/logging.py` (called from `app/main.py` before anything else is imported):

- **JSON lines on stdout** (`JsonFormatter`) — one JSON object per log line (timestamp, level, logger name, `request_id`, message, plus any `extra={...}` fields merged in), so logs can be shipped to and queried by a log aggregator (Loki/ELK/CloudWatch/Grafana) instead of grepped as free text.
- **Request-ID correlation**: `request_id_var` (a `contextvars.ContextVar`) holds the current request's ID and is stamped onto every log record by `RequestIdFilter`, so every log line emitted while handling one HTTP request — across `routes.py` → `rag_service.py` → `retrieve.py` — carries the same `request_id` without it being threaded through function signatures.
- **Log level**: controlled via `LOG_LEVEL` env var (`settings.log_level`, default `INFO`). Noisy third-party loggers (`httpx`, `httpcore`, `urllib3`, `chromadb`, `sentence_transformers`) are held to a separate, quieter level via `LOG_LEVEL_LIBS` (default `WARNING`) so they don't drown out the RAG pipeline's own logs.

### Request ID

The `add_request_id` middleware in `app/main.py` reads `X-Request-ID` from the incoming request (or generates one via `new_request_id()`), sets it on the context var for the duration of the request, echoes it back on the response's `X-Request-ID` header, and logs one `"request completed"` line per request with method/path/status/duration. This same ID is what error responses use as `instance` (see below), so a user-reported error can be matched directly to its log lines.

### Error handling

All error responses use the **RFC 9457 "Problem Details for HTTP APIs"** shape (`app/core/errors.py`, `ProblemDetail`), registered via `register_exception_handlers(app)` in `app/main.py`. Every error path — app-raised, validation, HTTP, or an unhandled exception — returns the same JSON body (`type`, `title`, `status`, `detail`, `instance`) with `Content-Type: application/problem+json`, instead of routes inventing their own error bodies or unhandled exceptions collapsing into a bare 500.

- `AppError` (base class) → subclasses map specific failure modes to status codes, e.g. `UpstreamLLMError` (502, LLM unreachable) and `UpstreamLLMTimeoutError` (504, LLM call timed out) — both raised in `ask()` in `app/retrieval/retrieve.py` when the Ollama-backed `ChatOpenAI` call fails.
- Unexpected exceptions are caught by a catch-all handler, logged with `logger.exception(...)` (full traceback), and returned as a generic 500 — the client never sees internal exception details.

## Running the indexer

`app/indexing/index.py` loads a PDF, chunks it (token-aware `RecursiveCharacterTextSplitter`, sized against the `BAAI/bge-m3` tokenizer), embeds it, and writes it into the Chroma collection (`hp_indigo_manual`) on the ChromaDB server at `settings.chroma_host`/`settings.chroma_port`.

```bash
# Add/update this file's chunks (default, idempotent — safe to rerun as long as chunking params haven't changed)
uv run python -m app.indexing.index --file data/indigo_6600.pdf

# Wipe the entire collection first, then index only this file
uv run python -m app.indexing.index --file data/indigo_6600.pdf --replace
```

## Running the eval harness

`app/eval/run_eval.py` runs a golden Q&A set end-to-end through retrieval and the live LLM (via `ask()` in `app/retrieval/retrieve.py`), then writes per-question and summary metrics (retrieval hit rate, citation hit rate, keyword recall, latency) to `app/eval/results/`. Requires the Ollama endpoint reachable and the Chroma vector store populated.

Three golden Q&A sets exist — same 20 questions, one per required answer language — selected via `--lang`: `golden_qa_en.json` (English, default), `golden_qa_ru.json` (Russian), `golden_qa_he.json` (Hebrew). All three retrieve against the same single English-language `indigo_6600.pdf` corpus (see "Documentation corpus" above) — the RU/HE runs test cross-lingual retrieval and answer-language compliance, not a translated corpus.

```bash
uv run python -m app.eval.run_eval           # English (default)
uv run python -m app.eval.run_eval --lang ru  # Russian
uv run python -m app.eval.run_eval --lang he  # Hebrew
```

Flags:

- `--lang {en,ru,he}` — which golden Q&A set to evaluate. Default: `en`. Ignored if `--golden` is given.
- `--golden <path>` — explicit path to a golden Q&A JSON file; overrides `--lang`.
- `--out <path>` — explicit path for the output results JSON. If omitted, an informative filename is auto-generated under `app/eval/results/`.

Example with overrides:

```bash
uv run python -m app.eval.run_eval --golden app/eval/golden_qa_en.json --out app/eval/results/manual_run.json
```

## Target production profile (not yet built)

- Deployed in a printing house, **1–50 concurrent users**.
- As a REST API intended for production, it will need the usual hardening for an internal service handling live traffic — **without fanaticism** (proportionate to an internal tool, not a public multi-tenant SaaS):
  - **Authentication** on `/api/ask` (currently open).
  - **Request throttling / rate limiting** per client.
  - **Input validation** hardening beyond Pydantic's basic type checks (e.g. question length limits).
  - **Secrets management** — no secrets in code or committed config; `.env` is already gitignored.
  - Standard REST hygiene still to add: CORS policy, upstream call timeouts/circuit breaking beyond what's already handled for the LLM, API versioning strategy.
  - Structured/correlated logs suitable for shipping to a log aggregator or dashboard tooling are already in place (see "Structural features" above) — production work here is wiring them to an actual destination (e.g. Grafana/Loki), not building the logging itself.
- **Deployment**: runs in Docker containers (`Dockerfile`, `docker-compose.yml`), both the app and the LLM (the LLM is served separately via Ollama), deployable to on-prem servers or cloud.
- Needs an **evaluation harness** with a golden Q&A set to measure retrieval/answer quality as the corpus and prompting evolve — implemented, see "Running the eval harness" above.

## Known gaps / things to watch for when working here

- No auth or rate limiting on `/api/ask` yet — see "Target production profile" above.
- Chapter/section (beyond page number) is not derived/attached to sources yet — only document + page.
- Only one manual is indexed; the collection is named generically `hp_indigo_manual` — will need a strategy for multiple machine models sharing or being separated across collections/metadata.

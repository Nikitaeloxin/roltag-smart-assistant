# 1. RAG pipeline foundations: embedding model, chunking, retrieval, LLM

## Status

Accepted (initial values — not yet empirically tuned; see "Follow-up" below)

## Date

2026-09-15

## Context

The service is a RAG assistant that answers HP Indigo Digital Press maintenance questions
grounded in PDF technical manuals (see `CLAUDE.md`). Building it required four foundational
choices: how documents get embedded, how they get chunked before embedding, how chunks get
retrieved at query time, and which LLM generates the answer.

These choices were made while getting the pipeline working end to end for the first time,
mostly by following LangChain's own documentation/tutorials rather than by benchmarking
alternatives. This ADR records what was chosen and, honestly, how strong the reasoning behind
each choice actually is — so that weakly-justified values are visible and revisited
deliberately, instead of silently ossifying into "how it's always been."

## Decision

### 1. Embedding model: `BAAI/bge-m3`

`app/indexing/index.py` embeds chunks with `HuggingFaceEmbeddings(model_name="BAAI/bge-m3",
encode_kwargs={"normalize_embeddings": True})`.

- **Why**: the assistant must answer in whichever language the user asked in — confirmed
  required languages are English, Russian, and Hebrew (`CLAUDE.md` — "Multilingual"). bge-m3 is
  a multilingual embedding model (100+ languages) with strong published retrieval benchmarks,
  and runs locally on CPU, matching the project's local/self-hosted deployment constraint (no
  external embedding API dependency, no manual content leaving the deployment).
- **Not evaluated**: no other multilingual embedding model (e.g. `multilingual-e5`, `LaBSE`) or
  hosted embedding API was benchmarked against it on this corpus. The choice is reasoned but not
  measured.

### 2. Text splitting: `RecursiveCharacterTextSplitter`, `chunk_size=1000`, `chunk_overlap=200`

`app/indexing/index.py` splits each PDF page with LangChain's `RecursiveCharacterTextSplitter`.

- **Why this splitter**: it is the splitter LangChain's own docs present as the standard
  general-purpose choice. It was adopted on that basis, not because alternatives (semantic
  chunking, a splitter tokenized against bge-m3's own tokenizer, or a structure-aware splitter
  that respects the manuals' section/procedure boundaries) were tried and rejected.
- **Why `chunk_size=1000` / `chunk_overlap=200`**: these are the example values from LangChain's
  tutorials, not values derived from this corpus — e.g. the typical length of a maintenance
  procedure or section in the HP Indigo manuals, or bge-m3's effective context window. No
  experimentation has been done to tune them.

### 3. Retrieval: Chroma `similarity_search`, `k=6`

`app/retrieval/retrieve.py` retrieves with `_load_vector_store().similarity_search(query, k=6)`
(`TOP_K_RESULTS = 6`).

- **Why plain similarity search**: it is Chroma/LangChain's default, single-call retrieval
  pattern shown in the tutorials — straightforward to wire up first.
- **Why `k=6`**: no specific rationale — carried over as "a reasonable-looking number" from the
  same tutorials, not chosen by measuring recall/precision on this corpus.
- **Not evaluated**: MMR (diversity-aware retrieval), hybrid search (vector + keyword/BM25), or
  varying `k` were not compared.

### 4. LLM: `qwen3:8b` via a remote Ollama instance

`app/core/config.py` defaults `llm_model_name` to `qwen3:8b`, served through an OpenAI-compatible
Ollama endpoint and called via `ChatOpenAI` (`app/retrieval/retrieve.py`).

- **Why local + this size**: the target deployment is on-prem, in a printing house, for 1–50
  concurrent users (`CLAUDE.md` — "Target production profile") — a self-hosted model avoids
  sending proprietary manual/machine content to an external API and avoids per-token cost for an
  internal tool. `qwen3:8b` was picked as a size tradeoff: small enough to run locally with
  modest hardware, larger/more capable than the smallest instruct models, aiming for usable
  answer precision without needing GPU-class resources.
- **Known open risk**: `CLAUDE.md` already flags that this model's generation quality in
  Russian/Hebrew is unconfirmed — an 8B instruct model may be materially weaker in non-English
  output than in English.
- **Not evaluated**: no other local model size/family was benchmarked on this task's actual
  question set before choosing `qwen3:8b`.

## Consequences

- **Positive**: a working end-to-end pipeline was reached quickly and safely, using
  well-documented, widely-used patterns while the author was still learning LangChain — this
  reduced implementation risk during initial build.
- **Negative**: `chunk_size`, `chunk_overlap`, retrieval `k`, and the embedding/LLM model
  choices are all currently untuned defaults borrowed from tutorials, not values validated
  against this corpus or this domain's questions. Retrieval and answer quality baselines are
  effectively unmeasured.

## Follow-up

An eval harness already exists (`app/eval/run_eval.py`, golden Q&A set in
`app/eval/golden_qa_en.json`) that measures retrieval hit rate, citation hit rate, keyword
recall, and latency, and already supports overriding `k` via `--k`. The values recorded in this
ADR should be treated as a starting point, not a conclusion — use the eval harness to:

- Sweep `chunk_size` / `chunk_overlap` and re-index to see their effect on retrieval hit rate.
- Sweep `k` (retrieval candidate count) for its effect on citation hit rate vs. latency/context
  size.
- Compare `BAAI/bge-m3` against at least one other multilingual embedding model on this corpus.
- Compare `qwen3:8b` against at least one other local model size on answer quality, especially
  for Russian/Hebrew questions.

## References

- `app/indexing/index.py` — embedding model, text splitter, chunk params
- `app/retrieval/retrieve.py` — retrieval call, `TOP_K_RESULTS`
- `app/core/config.py` — `llm_model_name`, `llm_base_url`
- `app/eval/run_eval.py` — eval harness for validating these choices empirically

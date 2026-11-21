"""Pipeline-identity constants for indexing and retrieval.

Single source of truth for what the RAG pipeline currently *is* (embedding
model, chunking strategy, retrieval strategy) — read by `app.indexing.index`
and `app.retrieval.retrieve` to configure the pipeline, and by
`app.eval.run_eval` to report which configuration a given eval run used.

Not deployment config (see `app.core.config.settings` for that, e.g.
`chroma_host`, `chroma_port`, `llm_base_url`) — these values are meant to change via a
code edit + re-index/re-eval, not via environment variables.
"""

#Indexing
EMBEDDING_MODEL_NAME = "BAAI/bge-m3"

#Chunking
TEXT_SPLITTER_NAME = "recursive-character"
CHUNK_SIZE = 1000
CHUNK_OVERLAP = 200

#Retrieval
RETRIEVAL_METHOD_NAME = "chroma-similarity"  # Chroma similarity_search
TOP_K_RESULTS = 6  # number of top documents to retrieve

import argparse
import logging
from pathlib import Path
from app.core.config import settings
from app.core.rag_config import (
    CHUNK_OVERLAP,
    CHUNK_SIZE,
    EMBEDDING_MODEL_NAME,
    TEXT_SPLITTER_NAME,
)

from langchain_core.documents import Document
from langchain_chroma import Chroma
from langchain_huggingface import HuggingFaceEmbeddings
import pypdf
from langchain_text_splitters import RecursiveCharacterTextSplitter

from app.core.logging import setup_logging

logger = logging.getLogger(__name__)

COLLECTION_NAME = "hp_indigo_manual"

def load_pdf_pages(file_path: str) -> list[Document]:
    reader = pypdf.PdfReader(file_path)
    labels = reader.page_labels
    return [
        Document(
            page_content=page.extract_text() or "",
            metadata={
                """enhanced metadata for each page, including page number and source file path, for using it in the answer generation"""
                "page_number": labels[i] if labels else str(i + 1),
                "physical_page": i + 1,
                "source": file_path,
            },
        )
        for i, page in enumerate(reader.pages)
    ]


def build_embeddings() -> HuggingFaceEmbeddings:
    return HuggingFaceEmbeddings(
        model_name=EMBEDDING_MODEL_NAME,
        encode_kwargs={"normalize_embeddings": True},
    )

def get_vector_store(embeddings: HuggingFaceEmbeddings) -> Chroma:
    return Chroma(
        collection_name=COLLECTION_NAME,
        embedding_function=embeddings,
        host=settings.chroma_host,
        port=settings.chroma_port,
    )


text_splitter = RecursiveCharacterTextSplitter(
    chunk_size=CHUNK_SIZE,
    chunk_overlap=CHUNK_OVERLAP,
    add_start_index=True
)


def ingest(file_path: str, mode: str) -> None:
    """mode: "add" upserts this file's chunks (safe to rerun, no duplicates
    as long as chunking params haven't changed). "replace" wipes the entire
    collection first, then adds only this file."""
    logger.info("loading pdf", extra={"file_path": file_path})
    docs = load_pdf_pages(file_path)
    logger.info("pages loaded", extra={"num_pages": len(docs)})

    all_splits = text_splitter.split_documents(docs)
    logger.info("chunks created", extra={"num_chunks": len(all_splits)})

    embeddings = build_embeddings()
    vector_store = get_vector_store(embeddings)

    if mode == "replace":
        logger.info("replace mode: wiping collection", extra={"collection": COLLECTION_NAME})
        vector_store.reset_collection()

    filename = Path(file_path).name
    ids = [f"{filename}:{i}" for i in range(len(all_splits))]
    vector_store.add_documents(all_splits, ids=ids)

    logger.info(
        "ingestion done",
        extra={"chunks_stored": vector_store._collection.count(), "mode": mode},
    )


if __name__ == "__main__":
    setup_logging()

    parser = argparse.ArgumentParser(description="Index a PDF manual into the Chroma vector store.")
    parser.add_argument("--file", required=True, help="Path to the PDF file to index.")
    mode_group = parser.add_mutually_exclusive_group()
    mode_group.add_argument(
        "--add", action="store_true", help="Add/update this file's chunks (default, idempotent)."
    )
    mode_group.add_argument(
        "--replace", action="store_true", help="Wipe the entire collection, then add only this file."
    )
    args = parser.parse_args()

    ingest(args.file, mode="replace" if args.replace else "add")

"""Compare RAG answers against the golden Q&A set.

Usage:
    uv run python -m app.eval.run_eval
    uv run python -m app.eval.run_eval --k 4 --golden app/eval/golden_qa_en.json
"""
import argparse
import json
import re
import time
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path

from app.core.config import settings
from app.core.rag_config import (
    EMBEDDING_MODEL_NAME,
    RETRIEVAL_METHOD_NAME,
    TEXT_SPLITTER_NAME,
    TOP_K_RESULTS,
)
from app.retrieval.retrieve import ask, retrieve_documents

EVAL_DIR = Path(__file__).parent
DEFAULT_GOLDEN = EVAL_DIR / "golden_qa_en.json"
RU_GOLDEN = EVAL_DIR / "golden_qa_ru.json"
HE_GOLDEN = EVAL_DIR / "golden_qa_he.json"

GOLDEN_BY_LANG = {"en": DEFAULT_GOLDEN, "ru": RU_GOLDEN, "he": HE_GOLDEN}


@dataclass
class QuestionResult:
    id: str
    question: str
    category: str
    expected_answer: str
    actual_answer: str
    expected_document: str
    expected_page: str
    retrieved_hit: bool
    retrieved_rank: int | None
    cited_sources: list[dict]
    citation_hit: bool
    keyword_recall: float
    elapsed_ms: float
    error: str | None = None


def normalize(text: str) -> str:
    return re.sub(r"[^a-z0-9 ]", " ", text.lower())


def key_terms(expected_answer: str) -> set[str]:
    tokens = normalize(expected_answer).split()
    return {t for t in tokens if len(t) > 3 or t.isdigit()}


def keyword_recall(expected_answer: str, actual_answer: str) -> float:
    terms = key_terms(expected_answer)
    if not terms:
        return 1.0
    actual_norm = normalize(actual_answer)
    hits = sum(1 for term in terms if term in actual_norm)
    return hits / len(terms)


def check_retrieval(question: str, expected_doc: str, expected_page: str) -> tuple[bool, int | None]:
    results = retrieve_documents(question)
    for rank, (doc) in enumerate(results, start=1):
        source_name = Path(doc.metadata.get("source", "")).name
        if source_name == expected_doc and str(doc.metadata.get("page_number")) == str(expected_page):
            return True, rank
    return False, None


def run_eval(golden_path: Path) -> list[QuestionResult]:
    golden = json.loads(golden_path.read_text())
    results: list[QuestionResult] = []

    for item in golden:
        expected_doc = item["source"]["document"]
        expected_page = item["source"]["page"]

        retrieved_hit, retrieved_rank = check_retrieval(item["question"], expected_doc, expected_page)

        answer_text = ""
        cited_sources: list[dict] = []
        error = None
        start = time.perf_counter()
        try:
            response = ask(item["question"])
            answer_text = response.answer
            cited_sources = [{"document": s.document, "page": s.page} for s in response.sources]
        except Exception as exc:
            error = str(exc)
        elapsed_ms = round((time.perf_counter() - start) * 1000, 1)

        citation_hit = any(
            src["document"] and Path(src["document"]).name == expected_doc and str(src["page"]) == str(expected_page)
            for src in cited_sources
        )

        result = QuestionResult(
            id=item["id"],
            question=item["question"],
            category=item.get("category", ""),
            expected_answer=item["expected_answer"],
            actual_answer=answer_text,
            expected_document=expected_doc,
            expected_page=expected_page,
            retrieved_hit=retrieved_hit,
            retrieved_rank=retrieved_rank,
            cited_sources=cited_sources,
            citation_hit=citation_hit,
            keyword_recall=round(keyword_recall(item["expected_answer"], answer_text), 3),
            elapsed_ms=elapsed_ms,
            error=error,
        )
        results.append(result)

        print(
            f"[{result.id}] retrieval_hit={retrieved_hit} rank={retrieved_rank} "
            f"citation_hit={citation_hit} keyword_recall={result.keyword_recall}"
            + (f" ERROR={error}" if error else "")
        )

    return results


def summarize(results: list[QuestionResult]) -> dict:
    n = len(results)
    ok = [r for r in results if r.error is None]
    return {
        "num_questions": n,
        "num_errors": n - len(ok),
        "retrieval_hit_rate": round(sum(r.retrieved_hit for r in results) / n, 3),
        "citation_hit_rate": round(sum(r.citation_hit for r in ok) / len(ok), 3) if ok else 0.0,
        "avg_keyword_recall": round(sum(r.keyword_recall for r in ok) / len(ok), 3) if ok else 0.0,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Evaluate RAG pipeline against a golden Q&A set")
    parser.add_argument("--golden", type=Path, default=None, help="Explicit path to a golden Q&A file; overrides --lang.")
    parser.add_argument("--out", type=Path, default=None)
    parser.add_argument(
        "--lang",
        choices=sorted(GOLDEN_BY_LANG),
        default="en",
        help="Which golden Q&A set to evaluate (default: en). Ignored if --golden is given.",
    )
    args = parser.parse_args()

    golden_path = args.golden or GOLDEN_BY_LANG[args.lang]
    results = run_eval(golden_path)
    summary = summarize(results)

    print("\n=== Summary ===")
    for key, value in summary.items():
        print(f"{key}: {value}")

    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    out_path = args.out or (EVAL_DIR / "results" / f"eval_result_{timestamp}.json")
    config = {
        "top_k": TOP_K_RESULTS,
        "embedding_model": EMBEDDING_MODEL_NAME,
        "retrieval_method": RETRIEVAL_METHOD_NAME,
        "text_splitter": TEXT_SPLITTER_NAME,
        "llm_model": settings.llm_model_name,
        "timestamp": timestamp,
    }
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(
        json.dumps(
            {"config": config, "summary": summary, "results": [asdict(r) for r in results]},
            indent=2,
            ensure_ascii=False,
        )
    )
    print(f"\nWrote detailed results to {out_path}")


if __name__ == "__main__":
    main()

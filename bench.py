"""Run the shared university-admissions retrieval benchmark.

Change only CHUNKER below to compare a different chunking strategy while
keeping documents, metadata, embeddings, and benchmark queries fixed.
"""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

from src import (
    Document,
    EmbeddingStore,
    GatewayChat,
    KnowledgeBaseAgent,
    NVIDIA_API_KEY_ENV,
    NvidiaChat,
    NvidiaEmbedder,
    OpenAIEmbedder,
    _mock_embed,
)
from src.heading_chunker import HeadingChunker

DATA_DIRECTORY = Path("data/university-admissions")

# Allow `python bench.py` to use the key stored in the project's .env file.
load_dotenv(override=False)

# Change this one line to compare another strategy fairly.
CHUNKER = HeadingChunker(chunk_size=800)

# OpenAI embeddings take precedence when OPENAI_API_KEY is available. NVIDIA
# remains available for GPT-OSS answers, or as an embedding fallback.
USE_OPENAI = bool(os.getenv("OPENAI_API_KEY"))
USE_NVIDIA = bool(os.getenv(NVIDIA_API_KEY_ENV))

BENCHMARKS = [
    {
        "query": "Ngưỡng đầu vào theo điểm thi tốt nghiệp THPT năm 2025 là bao nhiêu? Ngành Thiết kế vi mạch có yêu cầu riêng gì?",
        "gold_doc_id": "2025-phuong-thuc-tuyen-sinh-nam-2025",
        "metadata_filter": None,
    },
    {
        "query": "Điều kiện điểm SAT để xét tuyển theo chứng chỉ quốc tế là gì?",
        "gold_doc_id": "2025-phuong-thuc-tuyen-sinh-nam-2025",
        "metadata_filter": None,
    },
    {
        "query": "Thí sinh đạt giải cao trong kỳ thi uy tín đăng ký thông tin trong thời gian nào?",
        "gold_doc_id": "2025-phuong-thuc-tuyen-sinh-nam-2025",
        "metadata_filter": None,
    },
    {
        "query": "Ngành Kỹ thuật Máy tính tại UIT có hai hướng chuyên sâu nào?",
        "gold_doc_id": "nganh-ky-thuat-may-tinh",
        "metadata_filter": None,
    },
    {
        "query": "Chương trình Khoa học Máy tính liên kết quốc tế kéo dài bao lâu và có các lựa chọn địa điểm học nào?",
        "gold_doc_id": "nganh-khoa-hoc-may-tinh-chuong-trinh-lien-ket-quoc-te",
        "metadata_filter": {"audience": "student"},
    },
]


def read_frontmatter(path: Path) -> tuple[dict[str, str], str]:
    """Return simple YAML frontmatter and the Markdown body without PyYAML."""
    raw_text = path.read_text(encoding="utf-8")
    if not raw_text.startswith("---\n"):
        return {}, raw_text

    _, frontmatter, body = raw_text.split("---\n", 2)
    metadata: dict[str, str] = {}
    for line in frontmatter.splitlines():
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        metadata[key.strip()] = value.strip().strip('"\'')
    return metadata, body.lstrip()


def load_chunked_documents(directory: Path) -> list[Document]:
    documents: list[Document] = []
    for path in sorted(directory.glob("*.md")):
        metadata, content = read_frontmatter(path)
        doc_id = metadata.get("doc_id", path.stem)
        for index, chunk in enumerate(CHUNKER.chunk(content)):
            documents.append(
                Document(
                    id=f"{path.stem}#{index}",
                    content=chunk,
                    metadata={**metadata, "doc_id": doc_id, "chunk_index": index},
                )
            )
    return documents


def main() -> None:
    documents = load_chunked_documents(DATA_DIRECTORY)
    if USE_OPENAI:
        embedder = OpenAIEmbedder()
    elif USE_NVIDIA:
        embedder = NvidiaEmbedder()
    else:
        embedder = _mock_embed
    store = EmbeddingStore(collection_name="university_admissions", embedding_fn=embedder)
    store.add_documents(documents)
    # Chat answers use the local gateway. Embeddings keep their selected
    # backend above, so OPENAI_API_KEY continues to target OpenAI directly.
    llm_fn = GatewayChat()
    print(f"Loaded {len(documents)} chunks from {DATA_DIRECTORY}.")
    print(f"Embedding backend: {getattr(embedder, '_backend_name', 'mock')}")
    print(f"Answer backend: {llm_fn._backend_name}")

    for index, benchmark in enumerate(BENCHMARKS, start=1):
        metadata_filter = benchmark["metadata_filter"]
        if metadata_filter:
            results = store.search_with_filter(benchmark["query"], top_k=3, metadata_filter=metadata_filter)
        else:
            results = store.search(benchmark["query"], top_k=3)

        print(f"\n[{index}] {benchmark['query']}")
        print(f"Gold document: {benchmark['gold_doc_id']}; filter: {metadata_filter or 'none'}")
        for rank, result in enumerate(results, start=1):
            preview = " ".join(result["content"].split())[:180]
            print(
                f"  {rank}. score={result['score']:.3f} "
                f"doc_id={result['metadata']['doc_id']} "
                f"chunk={result['metadata']['chunk_index']}\n"
                f"     {preview}"
            )
        if llm_fn:
            answer = KnowledgeBaseAgent(store, llm_fn).answer(
                benchmark["query"], top_k=3, metadata_filter=metadata_filter
            )
            print(f"  Answer: {answer}")


if __name__ == "__main__":
    main()

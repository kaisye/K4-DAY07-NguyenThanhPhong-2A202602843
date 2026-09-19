from typing import Callable, Optional

from .store import EmbeddingStore


class KnowledgeBaseAgent:
    """
    An agent that answers questions using a vector knowledge base.

    Retrieval-augmented generation (RAG) pattern:
        1. Retrieve top-k relevant chunks from the store.
        2. Build a prompt with the chunks as context.
        3. Call the LLM to generate an answer.
    """

    def __init__(self, store: EmbeddingStore, llm_fn: Callable[[str], str]) -> None:
        self.store = store
        self.llm_fn = llm_fn

    def answer(
        self,
        question: str,
        top_k: int = 3,
        metadata_filter: Optional[dict] = None,
    ) -> str:
        if self.store.get_collection_size() == 0:
            return "Không tìm thấy tài liệu nào trong knowledge base để trả lời câu hỏi này."

        if metadata_filter:
            results = self.store.search_with_filter(
                question, top_k=top_k, metadata_filter=metadata_filter
            )
        else:
            results = self.store.search(question, top_k=top_k)
        if not results:
            return "Không tìm thấy ngữ cảnh liên quan trong knowledge base."

        context_blocks = []
        for index, result in enumerate(results, start=1):
            metadata = result["metadata"]
            source = metadata.get("source") or metadata.get("source_url") or metadata.get("doc_id", "không rõ nguồn")
            context_blocks.append(f"[{index}] Nguồn: {source}\n{result['content']}")

        context = "\n\n".join(context_blocks)
        prompt = (
            "Trả lời đầy đủ mọi ý và điều kiện được hỏi, chỉ dựa trên ngữ cảnh bên dưới. "
            "Nếu ngữ cảnh không đủ, hãy nói rõ rằng không tìm thấy thông tin. "
            "Khi dùng thông tin, hãy trích dẫn số chunk tương ứng, ví dụ [1].\n\n"
            f"Ngữ cảnh:\n{context}\n\n"
            f"Câu hỏi: {question}\n"
            "Trả lời:"
        )
        return self.llm_fn(prompt)

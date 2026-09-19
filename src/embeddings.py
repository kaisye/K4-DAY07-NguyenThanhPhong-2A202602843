from __future__ import annotations

import hashlib
import json
import math
import os
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

# Multilingual model suitable for the Vietnamese corpora used in this Lab.
# The local backend remains optional; required checkpoints use MockEmbedder.
LOCAL_EMBEDDING_MODEL = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
OPENAI_EMBEDDING_MODEL = "text-embedding-3-small"
GEMINI_EMBEDDING_MODEL = "gemini-embedding-001"
EMBEDDING_PROVIDER_ENV = "EMBEDDING_PROVIDER"
NVIDIA_API_KEY_ENV = "NVIDIA_API_KEY"
NVIDIA_API_BASE_URL = "https://integrate.api.nvidia.com/v1"
NVIDIA_EMBEDDING_MODEL = "nvidia/nemotron-3-embed-1b"
NVIDIA_CHAT_MODEL = "openai/gpt-oss-120b"
GATEWAY_BASE_URL = "http://127.0.0.1:20128/v1"
GATEWAY_CHAT_MODEL = "cx/gpt-5.5"
GATEWAY_API_KEY_ENV = "GATEWAY_API_KEY"


class MockEmbedder:
    """Deterministic embedding backend used by tests and default classroom runs."""

    def __init__(self, dim: int = 64) -> None:
        self.dim = dim
        self._backend_name = "mock embeddings fallback"

    def __call__(self, text: str) -> list[float]:
        digest = hashlib.md5(text.encode()).hexdigest()
        seed = int(digest, 16)
        vector = []
        for _ in range(self.dim):
            seed = (seed * 1664525 + 1013904223) & 0xFFFFFFFF
            vector.append((seed / 0xFFFFFFFF) * 2 - 1)
        norm = math.sqrt(sum(value * value for value in vector)) or 1.0
        return [value / norm for value in vector]


class LocalEmbedder:
    """Sentence Transformers-backed local embedder."""

    def __init__(self, model_name: str = LOCAL_EMBEDDING_MODEL) -> None:
        from sentence_transformers import SentenceTransformer

        self.model_name = model_name
        self._backend_name = model_name
        self.model = SentenceTransformer(model_name)

    def __call__(self, text: str) -> list[float]:
        embedding = self.model.encode(text, normalize_embeddings=True)
        if hasattr(embedding, "tolist"):
            return embedding.tolist()
        return [float(value) for value in embedding]


class OpenAIEmbedder:
    """OpenAI embeddings API-backed embedder."""

    def __init__(self, model_name: str = OPENAI_EMBEDDING_MODEL) -> None:
        from openai import OpenAI

        self.model_name = model_name
        self._backend_name = model_name
        self.client = OpenAI()

    def __call__(self, text: str) -> list[float]:
        response = self.client.embeddings.create(model=self.model_name, input=text)
        return [float(value) for value in response.data[0].embedding]

    def embed_many(self, texts: list[str]) -> list[list[float]]:
        """Embed all benchmark chunks in one API request."""
        if not texts:
            return []
        response = self.client.embeddings.create(model=self.model_name, input=texts)
        return [[float(value) for value in item.embedding] for item in response.data]


class GatewayChat:
    """LLM callable for the local OpenAI-compatible gateway.

    Its client has an explicit base URL, so configuring this gateway never
    changes the official OpenAI client used by :class:`OpenAIEmbedder`.
    """

    def __init__(
        self,
        model_name: str = GATEWAY_CHAT_MODEL,
        base_url: str = GATEWAY_BASE_URL,
        api_key: str | None = None,
        max_tokens: int = 500,
    ) -> None:
        from openai import OpenAI

        self.model_name = model_name
        self.base_url = base_url.rstrip("/")
        self.max_tokens = max_tokens
        # Many local OpenAI-compatible gateways accept any non-empty key.
        self.api_key = api_key or os.getenv(GATEWAY_API_KEY_ENV, "local-gateway")
        self._backend_name = f"{self.model_name} via {self.base_url}"
        self.client = OpenAI(base_url=self.base_url, api_key=self.api_key)

    def __call__(self, prompt: str) -> str:
        try:
            response = self.client.chat.completions.create(
                model=self.model_name,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.2,
                max_tokens=self.max_tokens,
            )
            return str(response.choices[0].message.content or "")
        except Exception as error:
            raise RuntimeError(
                f"Local gateway request failed ({self.base_url}, {self.model_name}): {error}"
            ) from error


class GeminiEmbedder:
    """Google Gemini embeddings API-backed embedder (google-genai SDK).

    Free-tier alternative to OpenAI for students without an OpenAI key —
    a Gemini API key (aistudio.google.com) has a free quota, no billing card needed.
    """

    def __init__(self, model_name: str = GEMINI_EMBEDDING_MODEL) -> None:
        from google import genai

        api_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
        if not api_key:
            raise RuntimeError("GEMINI_API_KEY (or GOOGLE_API_KEY) is required for GeminiEmbedder")
        self.model_name = model_name
        self._backend_name = model_name
        self.client = genai.Client(api_key=api_key)

    def __call__(self, text: str) -> list[float]:
        response = self.client.models.embed_content(model=self.model_name, contents=text)
        return [float(value) for value in response.embeddings[0].values]


def _nvidia_request(path: str, api_key: str, payload: dict) -> dict:
    """Send a JSON request to NVIDIA's hosted NIM API."""
    request = Request(
        f"{NVIDIA_API_BASE_URL}{path}",
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {api_key}",
            "Accept": "application/json",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    try:
        with urlopen(request, timeout=60) as response:
            return json.loads(response.read().decode("utf-8"))
    except HTTPError as error:
        detail = error.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"NVIDIA API request failed ({error.code}): {detail}") from error
    except URLError as error:
        raise RuntimeError(f"Could not reach the NVIDIA API: {error.reason}") from error


class NvidiaEmbedder:
    """Hosted NVIDIA NIM embedding backend for semantic retrieval."""

    def __init__(self, model_name: str = NVIDIA_EMBEDDING_MODEL, api_key: str | None = None) -> None:
        self.model_name = model_name
        self.api_key = api_key or os.getenv(NVIDIA_API_KEY_ENV)
        if not self.api_key:
            raise RuntimeError(f"{NVIDIA_API_KEY_ENV} is required for NvidiaEmbedder")
        self._backend_name = model_name

    def __call__(self, text: str) -> list[float]:
        if not text:
            raise ValueError("Cannot embed empty text")
        response = _nvidia_request(
            "/embeddings",
            self.api_key,
            {"model": self.model_name, "input": text, "encoding_format": "float"},
        )
        try:
            return [float(value) for value in response["data"][0]["embedding"]]
        except (KeyError, IndexError, TypeError) as error:
            raise RuntimeError(f"Unexpected NVIDIA embedding response: {response}") from error


class NvidiaChat:
    """Callable LLM function backed by NVIDIA NIM's gpt-oss chat endpoint."""

    def __init__(
        self,
        model_name: str = NVIDIA_CHAT_MODEL,
        api_key: str | None = None,
        max_tokens: int = 500,
    ) -> None:
        self.model_name = model_name
        self.api_key = api_key or os.getenv(NVIDIA_API_KEY_ENV)
        self.max_tokens = max_tokens
        if not self.api_key:
            raise RuntimeError(f"{NVIDIA_API_KEY_ENV} is required for NvidiaChat")
        self._backend_name = model_name

    def __call__(self, prompt: str) -> str:
        response = _nvidia_request(
            "/chat/completions",
            self.api_key,
            {
                "model": self.model_name,
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.2,
                "max_tokens": self.max_tokens,
            },
        )
        try:
            return str(response["choices"][0]["message"]["content"] or "")
        except (KeyError, IndexError, TypeError) as error:
            raise RuntimeError(f"Unexpected NVIDIA chat response: {response}") from error


_mock_embed = MockEmbedder()

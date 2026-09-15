"""Local ChromaDB vector store.

INVARIANTS enforced here:
  * Storage is local and private — a persistent on-disk Chroma directory, no
    hosted vector database, no per-vector fees, nothing leaves the machine.
  * Every stored vector keeps {"source", "page", "chunk_id"}. add_chunks
    refuses to write a chunk whose metadata is incomplete.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol, Sequence

import chromadb
from chromadb.config import Settings

from rag.chunker import Chunk
from rag.config import (
    CHROMA_DIR,
    COLLECTION_NAME,
    EMBEDDING_BACKEND,
    EMBEDDING_MODEL,
    TOP_K,
)

REQUIRED_METADATA = ("source", "page", "chunk_id")


class Embedder(Protocol):
    """Anything that turns texts into vectors.

    A protocol rather than a hard dependency so tests can inject a cheap
    deterministic embedder, and so swapping all-MiniLM-L6-v2 for a hosted
    embedding model later touches one class instead of the store.
    """

    def encode(self, texts: Sequence[str]) -> list[list[float]]:  # pragma: no cover
        ...


@dataclass(frozen=True)
class Retrieved:
    """A retrieved chunk plus its similarity score."""

    text: str
    source: str
    page: int
    chunk_id: int
    section: str
    score: float  # cosine similarity in [0, 1]; higher is closer

    @property
    def citation(self) -> str:
        base = f"{self.source}, Page {self.page}"
        return f"{base}, Section {self.section}" if self.section else base


class _Embedder:
    """Lazy sentence-transformers wrapper.

    Loaded on first use, not on import, so `python -c "import rag"` stays fast
    and the Streamlit app can show a spinner while the model warms up.
    """

    def __init__(self, model_name: str = EMBEDDING_MODEL) -> None:
        self.model_name = model_name
        self._model: Any = None

    @property
    def model(self) -> Any:
        if self._model is None:
            from sentence_transformers import SentenceTransformer

            self._model = SentenceTransformer(self.model_name)
        return self._model

    def encode(self, texts: Sequence[str], batch_size: int = 32) -> list[list[float]]:
        vectors = self.model.encode(
            list(texts),
            batch_size=batch_size,
            show_progress_bar=False,
            normalize_embeddings=True,  # unit vectors -> cosine distance is exact
            convert_to_numpy=True,
        )
        return [v.tolist() for v in vectors]


class _OnnxEmbedder:
    """all-MiniLM-L6-v2 via chromadb's bundled quantized ONNX build.

    Same model as the sentence-transformers path, without torch. The weights
    (~80 MB) are fetched on first use and cached, so a cold Streamlit Cloud
    boot pays that download once.

    Chroma's implementation L2-normalises its output, exactly as the
    sentence-transformers path does with normalize_embeddings=True, so
    `1 - cosine_distance` remains an exact cosine similarity either way.
    """

    def __init__(self, model_name: str = EMBEDDING_MODEL) -> None:
        self.model_name = f"{model_name} (onnx)"
        self._fn: Any = None

    @property
    def fn(self) -> Any:
        if self._fn is None:
            from chromadb.utils import embedding_functions

            self._fn = embedding_functions.ONNXMiniLM_L6_V2()
        return self._fn

    def encode(self, texts: Sequence[str]) -> list[list[float]]:
        return [list(map(float, vector)) for vector in self.fn(list(texts))]


def default_embedder(backend: str = EMBEDDING_BACKEND) -> Embedder:
    """Pick the embedding runtime. Unknown values fall back to ONNX.

    Falling back rather than raising is deliberate: a typo in an env var on a
    deployed demo should not take the app down.
    """
    if backend in ("sentence-transformers", "sentence_transformers", "st"):
        return _Embedder(EMBEDDING_MODEL)
    return _OnnxEmbedder(EMBEDDING_MODEL)


class VectorStore:
    def __init__(
        self,
        persist_dir: str | Path = CHROMA_DIR,
        collection_name: str = COLLECTION_NAME,
        embedding_model: str = EMBEDDING_MODEL,
        embedder: Embedder | None = None,
    ) -> None:
        self.persist_dir = Path(persist_dir)
        self.persist_dir.mkdir(parents=True, exist_ok=True)
        self.collection_name = collection_name
        self.embedder: Embedder = embedder or default_embedder()
        self.client = chromadb.PersistentClient(
            path=str(self.persist_dir),
            settings=Settings(anonymized_telemetry=False, allow_reset=True),
        )
        self.collection = self.client.get_or_create_collection(
            name=collection_name,
            metadata={
                "hnsw:space": "cosine",
                "embedding_model": embedding_model,
                "embedding_backend": EMBEDDING_BACKEND,
            },
        )

    # --- writing ---

    def add_chunks(self, chunks: Sequence[Chunk], batch_size: int = 128) -> int:
        """Upsert chunks. Returns the number written.

        Upsert, not add: re-running ingestion on an edited document replaces its
        chunks in place instead of duplicating them, because Chunk.id is derived
        from source + page + chunk_id.
        """
        if not chunks:
            return 0

        for chunk in chunks:
            metadata = chunk.metadata()
            missing = [k for k in REQUIRED_METADATA if metadata.get(k) in (None, "")]
            if missing:
                raise ValueError(
                    f"Refusing to index a chunk missing required metadata {missing}: "
                    f"{chunk.id!r}. An uncited answer is a bug — see README invariant 3."
                )

        written = 0
        for start in range(0, len(chunks), batch_size):
            batch = chunks[start : start + batch_size]
            texts = [c.text for c in batch]
            self.collection.upsert(
                ids=[c.id for c in batch],
                documents=texts,
                metadatas=[c.metadata() for c in batch],
                embeddings=self.embedder.encode(texts),
            )
            written += len(batch)
        return written

    # --- reading ---

    def query(
        self,
        question: str,
        top_k: int = TOP_K,
        source: str | None = None,
    ) -> list[Retrieved]:
        """Return the top_k most similar chunks, optionally scoped to one source."""
        if not question.strip():
            return []
        if self.count() == 0:
            return []

        where = {"source": source} if source else None
        result = self.collection.query(
            query_embeddings=self.embedder.encode([question]),
            n_results=min(top_k, self.count()),
            where=where,
            include=["documents", "metadatas", "distances"],
        )

        documents = result.get("documents") or [[]]
        metadatas = result.get("metadatas") or [[]]
        distances = result.get("distances") or [[]]

        retrieved: list[Retrieved] = []
        for text, metadata, distance in zip(documents[0], metadatas[0], distances[0]):
            retrieved.append(
                Retrieved(
                    text=text,
                    source=str(metadata.get("source", "")),
                    page=int(metadata.get("page", 0)),
                    chunk_id=int(metadata.get("chunk_id", 0)),
                    section=str(metadata.get("section", "")),
                    # Chroma returns cosine *distance*; embeddings are normalised.
                    score=round(1.0 - float(distance), 4),
                )
            )
        return retrieved

    def count(self) -> int:
        return self.collection.count()

    def sources(self) -> list[str]:
        """Distinct source filenames currently indexed, for the sidebar picker."""
        if self.count() == 0:
            return []
        got = self.collection.get(include=["metadatas"])
        names = {str(m.get("source", "")) for m in (got.get("metadatas") or [])}
        return sorted(n for n in names if n)

    def reset(self) -> None:
        """Drop and recreate the collection — a clean re-index."""
        self.client.delete_collection(self.collection_name)
        self.collection = self.client.get_or_create_collection(
            name=self.collection_name,
            metadata={"hnsw:space": "cosine"},
        )

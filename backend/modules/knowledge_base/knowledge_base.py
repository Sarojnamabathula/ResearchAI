"""
ResearchAI — Module 4: Knowledge Base (Vector Store)
Manages embedding generation and vector storage using ChromaDB (default)
or FAISS. Provides semantic similarity search over paper chunks.
"""

from __future__ import annotations
import json
import uuid
from typing import List, Tuple, Optional, Dict, Any

from researchai.backend.core.models import PaperChunk, RAGContext
from researchai.backend.core.logger import get_logger
from researchai.backend.core.exceptions import VectorStoreError
from researchai.backend.core.watsonx_client import get_watsonx_client
from researchai.config import settings

logger = get_logger("knowledge_base")


# ---------------------------------------------------------------------------
# Embedding Generator
# ---------------------------------------------------------------------------

class EmbeddingGenerator:
    """Generates text embeddings using IBM watsonx or sentence-transformers."""

    def __init__(self) -> None:
        self.client = get_watsonx_client()

    def embed_texts(self, texts: List[str]) -> List[List[float]]:
        """Return a list of embedding vectors for the given texts."""
        return self.client.embed(texts)

    def embed_query(self, query: str) -> List[float]:
        return self.embed_texts([query])[0]


# ---------------------------------------------------------------------------
# ChromaDB Vector Store
# ---------------------------------------------------------------------------

class ChromaVectorStore:
    """Persistent ChromaDB collection for paper chunks."""

    COLLECTION_NAME = "researchai_papers"

    def __init__(self) -> None:
        self._client = None
        self._collection = None
        self._setup()

    def _setup(self) -> None:
        try:
            import chromadb
            from chromadb.config import Settings as ChromaSettings
            self._client = chromadb.PersistentClient(
                path=settings.CHROMA_PERSIST_DIR,
                settings=ChromaSettings(anonymized_telemetry=False),
            )
            self._collection = self._client.get_or_create_collection(
                name=self.COLLECTION_NAME,
                metadata={"hnsw:space": "cosine"},
            )
            logger.info(
                "ChromaDB collection '%s' ready (%d items)",
                self.COLLECTION_NAME,
                self._collection.count(),
            )
        except ImportError:
            logger.warning("chromadb not installed — vector store disabled")
            self._collection = None
        except Exception as exc:
            logger.error("ChromaDB setup failed: %s", exc)
            self._collection = None

    def add_chunks(
        self,
        chunks: List[PaperChunk],
        embeddings: List[List[float]],
    ) -> None:
        if self._collection is None:
            logger.warning("Vector store unavailable — skipping chunk storage")
            return
        ids = [f"{c.paper_id}__chunk_{c.chunk_index}" for c in chunks]
        docs = [c.text for c in chunks]
        metas = [
            {"paper_id": c.paper_id, "section": c.section or "", "chunk_index": c.chunk_index}
            for c in chunks
        ]
        self._collection.upsert(
            ids=ids,
            embeddings=embeddings,
            documents=docs,
            metadatas=metas,
        )
        logger.info("Added %d chunks to ChromaDB", len(chunks))

    def search(
        self,
        query_embedding: List[float],
        n_results: int = 5,
        paper_ids: Optional[List[str]] = None,
    ) -> List[Tuple[str, float, Dict]]:
        """Return list of (text, score, metadata) tuples."""
        if self._collection is None:
            return []
        where = {"paper_id": {"$in": paper_ids}} if paper_ids else None
        try:
            results = self._collection.query(
                query_embeddings=[query_embedding],
                n_results=min(n_results, max(1, self._collection.count())),
                where=where,
                include=["documents", "distances", "metadatas"],
            )
            docs = results.get("documents", [[]])[0]
            dists = results.get("distances", [[]])[0]
            metas = results.get("metadatas", [[]])[0]
            return [(doc, 1.0 - dist, meta) for doc, dist, meta in zip(docs, dists, metas)]
        except Exception as exc:
            logger.error("ChromaDB search error: %s", exc)
            return []

    def delete_paper(self, paper_id: str) -> None:
        if self._collection:
            self._collection.delete(where={"paper_id": paper_id})

    def count(self) -> int:
        return self._collection.count() if self._collection else 0


# ---------------------------------------------------------------------------
# FAISS Vector Store (alternative)
# ---------------------------------------------------------------------------

class FAISSVectorStore:
    """In-memory FAISS index with pickle persistence."""

    def __init__(self) -> None:
        self._index = None
        self._id_map: List[Dict] = []  # maps FAISS position -> metadata
        self._setup()

    def _setup(self) -> None:
        try:
            import faiss
            import numpy as np
            dim = settings.EMBEDDING_DIMENSION
            self._index = faiss.IndexFlatIP(dim)  # Inner Product (cosine after normalisation)
            # Try loading existing index
            import pickle
            idx_path = settings.FAISS_INDEX_PATH
            if idx_path and Path(idx_path).exists():
                with open(idx_path, "rb") as f:
                    saved = pickle.load(f)
                self._index = saved["index"]
                self._id_map = saved["id_map"]
                logger.info("Loaded FAISS index: %d vectors", self._index.ntotal)
        except ImportError:
            logger.warning("faiss not installed")
        except Exception as exc:
            logger.error("FAISS setup error: %s", exc)

    def add_chunks(self, chunks: List[PaperChunk], embeddings: List[List[float]]) -> None:
        if self._index is None:
            return
        import numpy as np
        import faiss
        vecs = np.array(embeddings, dtype="float32")
        faiss.normalize_L2(vecs)
        self._index.add(vecs)
        for chunk in chunks:
            self._id_map.append({
                "paper_id": chunk.paper_id,
                "text": chunk.text,
                "section": chunk.section or "",
            })
        self._persist()

    def search(
        self,
        query_embedding: List[float],
        n_results: int = 5,
        paper_ids: Optional[List[str]] = None,
    ) -> List[Tuple[str, float, Dict]]:
        if self._index is None or self._index.ntotal == 0:
            return []
        import numpy as np
        import faiss
        vec = np.array([query_embedding], dtype="float32")
        faiss.normalize_L2(vec)
        scores, indices = self._index.search(vec, min(n_results * 3, self._index.ntotal))
        results = []
        for score, idx in zip(scores[0], indices[0]):
            if idx < 0:
                continue
            meta = self._id_map[idx]
            if paper_ids and meta["paper_id"] not in paper_ids:
                continue
            results.append((meta["text"], float(score), meta))
            if len(results) >= n_results:
                break
        return results

    def _persist(self) -> None:
        try:
            import pickle
            from pathlib import Path
            idx_path = settings.FAISS_INDEX_PATH
            if idx_path:
                Path(idx_path).parent.mkdir(parents=True, exist_ok=True)
                with open(idx_path, "wb") as f:
                    pickle.dump({"index": self._index, "id_map": self._id_map}, f)
        except Exception as exc:
            logger.warning("FAISS persist error: %s", exc)


# ---------------------------------------------------------------------------
# Knowledge Base Service
# ---------------------------------------------------------------------------

from pathlib import Path  # noqa: E402

class KnowledgeBase:
    """
    High-level knowledge base service.
    Chooses between ChromaDB and FAISS based on settings.
    Provides add_paper() and semantic_search() for the rest of the system.
    """

    def __init__(self) -> None:
        self.embedder = EmbeddingGenerator()
        if settings.VECTOR_STORE_TYPE == "faiss":
            self.store = FAISSVectorStore()
        else:
            self.store = ChromaVectorStore()

    def add_paper_chunks(self, chunks: List[PaperChunk]) -> None:
        """Embed and store all chunks for a paper."""
        texts = [c.text for c in chunks]
        embeddings = self.embedder.embed_texts(texts)
        self.store.add_chunks(chunks, embeddings)

    def semantic_search(
        self,
        query: str,
        n_results: int = None,
        paper_ids: Optional[List[str]] = None,
    ) -> RAGContext:
        """Embed the query and retrieve the top-k most relevant chunks."""
        n = n_results or settings.TOP_K_RESULTS
        q_emb = self.embedder.embed_query(query)
        raw = self.store.search(q_emb, n_results=n, paper_ids=paper_ids)

        chunks: List[PaperChunk] = []
        scores: List[float] = []
        source_ids: List[str] = []

        for text, score, meta in raw:
            paper_id = meta.get("paper_id", "")
            chunks.append(PaperChunk(
                paper_id=paper_id,
                chunk_index=meta.get("chunk_index", 0),
                text=text,
                section=meta.get("section"),
            ))
            scores.append(score)
            if paper_id not in source_ids:
                source_ids.append(paper_id)

        return RAGContext(
            query=query,
            retrieved_chunks=chunks,
            source_paper_ids=source_ids,
            retrieval_scores=scores,
        )

    def count(self) -> int:
        return self.store.count()

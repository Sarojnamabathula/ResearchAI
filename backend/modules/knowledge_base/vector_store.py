"""
ResearchAI — Module 4: Knowledge Base / Vector Store
Supports ChromaDB (default) and FAISS as pluggable backends.
Handles embedding generation, storage, and semantic similarity search.
"""

from __future__ import annotations
from typing import List, Tuple, Optional
import json

from researchai.backend.core.models import PaperChunk
from researchai.backend.core.exceptions import VectorStoreError
from researchai.backend.core.logger import get_logger
from researchai.backend.core.watsonx_client import get_watsonx_client
from researchai.config import settings

logger = get_logger("vector_store")


class VectorStore:
    """
    Unified interface over ChromaDB and FAISS vector stores.
    Backend is selected via settings.VECTOR_STORE_TYPE.
    """

    def __init__(self) -> None:
        self.client = get_watsonx_client()
        self._backend = settings.VECTOR_STORE_TYPE.lower()
        self._collection = None
        self._faiss_index = None
        self._faiss_metadata: List[dict] = []
        self._init_backend()

    # ------------------------------------------------------------------
    # Initialisation
    # ------------------------------------------------------------------

    def _init_backend(self) -> None:
        if self._backend == "chromadb":
            self._init_chroma()
        elif self._backend == "faiss":
            self._init_faiss()
        else:
            logger.warning("Unknown vector store backend '%s'; defaulting to chromadb", self._backend)
            self._backend = "chromadb"
            self._init_chroma()

    def _init_chroma(self) -> None:
        try:
            import chromadb
            client = chromadb.PersistentClient(path=settings.CHROMA_PERSIST_DIR)
            self._collection = client.get_or_create_collection(
                name="research_papers",
                metadata={"hnsw:space": "cosine"},
            )
            logger.info("ChromaDB initialised at %s", settings.CHROMA_PERSIST_DIR)
        except ImportError:
            raise VectorStoreError("chromadb not installed. Run: pip install chromadb")
        except Exception as exc:
            raise VectorStoreError(f"ChromaDB init failed: {exc}") from exc

    def _init_faiss(self) -> None:
        try:
            import faiss
            import numpy as np
            import os
            index_path = settings.FAISS_INDEX_PATH
            meta_path = index_path + ".meta.json"
            dim = settings.EMBEDDING_DIMENSION

            if os.path.exists(index_path):
                self._faiss_index = faiss.read_index(index_path)
                with open(meta_path, "r") as f:
                    self._faiss_metadata = json.load(f)
                logger.info("FAISS index loaded from %s (%d vectors)",
                            index_path, self._faiss_index.ntotal)
            else:
                self._faiss_index = faiss.IndexFlatCosine(dim)
                self._faiss_metadata = []
                logger.info("New FAISS index created (dim=%d)", dim)
        except ImportError:
            raise VectorStoreError("faiss-cpu not installed. Run: pip install faiss-cpu")
        except Exception as exc:
            raise VectorStoreError(f"FAISS init failed: {exc}") from exc

    # ------------------------------------------------------------------
    # Indexing
    # ------------------------------------------------------------------

    def add_chunks(self, chunks: List[PaperChunk]) -> None:
        """Embed a list of PaperChunks and add to the store."""
        if not chunks:
            return
        texts = [c.text for c in chunks]
        embeddings = self.client.embed(texts)

        if self._backend == "chromadb":
            self._chroma_add(chunks, embeddings)
        else:
            self._faiss_add(chunks, embeddings)

        logger.info("Indexed %d chunks for paper_id=%s",
                    len(chunks), chunks[0].paper_id if chunks else "?")

    def _chroma_add(self, chunks: List[PaperChunk],
                    embeddings: List[List[float]]) -> None:
        ids = [f"{c.paper_id}_{c.chunk_index}" for c in chunks]
        metadatas = [
            {"paper_id": c.paper_id, "chunk_index": c.chunk_index,
             "section": c.section or "", "page_number": c.page_number or 0}
            for c in chunks
        ]
        documents = [c.text for c in chunks]
        # Upsert in batches of 100
        batch = 100
        for i in range(0, len(ids), batch):
            self._collection.upsert(
                ids=ids[i:i+batch],
                embeddings=embeddings[i:i+batch],
                documents=documents[i:i+batch],
                metadatas=metadatas[i:i+batch],
            )

    def _faiss_add(self, chunks: List[PaperChunk],
                   embeddings: List[List[float]]) -> None:
        import numpy as np
        vecs = np.array(embeddings, dtype="float32")
        self._faiss_index.add(vecs)
        for c, emb in zip(chunks, embeddings):
            self._faiss_metadata.append({
                "paper_id": c.paper_id,
                "chunk_index": c.chunk_index,
                "text": c.text,
                "section": c.section or "",
            })
        self._save_faiss()

    def _save_faiss(self) -> None:
        import faiss
        faiss.write_index(self._faiss_index, settings.FAISS_INDEX_PATH)
        with open(settings.FAISS_INDEX_PATH + ".meta.json", "w") as f:
            json.dump(self._faiss_metadata, f)

    # ------------------------------------------------------------------
    # Retrieval
    # ------------------------------------------------------------------

    def search(self, query: str, top_k: int = None,
               paper_ids: Optional[List[str]] = None) -> List[Tuple[PaperChunk, float]]:
        """
        Semantic search over indexed chunks.
        Returns a list of (PaperChunk, score) tuples sorted by relevance.
        """
        k = top_k or settings.TOP_K_RESULTS
        query_embedding = self.client.embed([query])[0]

        if self._backend == "chromadb":
            return self._chroma_search(query, query_embedding, k, paper_ids)
        else:
            return self._faiss_search(query_embedding, k, paper_ids)

    def _chroma_search(self, query: str, embedding: List[float],
                       k: int, paper_ids: Optional[List[str]]) -> List[Tuple[PaperChunk, float]]:
        where = {"paper_id": {"$in": paper_ids}} if paper_ids else None
        kwargs = dict(
            query_embeddings=[embedding],
            n_results=min(k, max(self._collection.count(), 1)),
            include=["documents", "metadatas", "distances"],
        )
        if where:
            kwargs["where"] = where
        results = self._collection.query(**kwargs)

        output = []
        docs = results.get("documents", [[]])[0]
        metas = results.get("metadatas", [[]])[0]
        dists = results.get("distances", [[]])[0]
        for doc, meta, dist in zip(docs, metas, dists):
            score = 1.0 - dist  # cosine distance → similarity
            chunk = PaperChunk(
                paper_id=meta.get("paper_id", ""),
                chunk_index=meta.get("chunk_index", 0),
                text=doc,
                section=meta.get("section") or None,
                page_number=meta.get("page_number") or None,
            )
            output.append((chunk, round(score, 4)))
        return output

    def _faiss_search(self, embedding: List[float],
                      k: int, paper_ids: Optional[List[str]]) -> List[Tuple[PaperChunk, float]]:
        import numpy as np
        if self._faiss_index.ntotal == 0:
            return []
        vec = np.array([embedding], dtype="float32")
        distances, indices = self._faiss_index.search(vec, min(k * 3, self._faiss_index.ntotal))
        output = []
        for dist, idx in zip(distances[0], indices[0]):
            if idx < 0 or idx >= len(self._faiss_metadata):
                continue
            meta = self._faiss_metadata[idx]
            if paper_ids and meta["paper_id"] not in paper_ids:
                continue
            chunk = PaperChunk(
                paper_id=meta["paper_id"],
                chunk_index=meta["chunk_index"],
                text=meta["text"],
                section=meta.get("section") or None,
            )
            output.append((chunk, round(float(dist), 4)))
            if len(output) >= k:
                break
        return sorted(output, key=lambda x: x[1], reverse=True)

    def count(self) -> int:
        if self._backend == "chromadb" and self._collection:
            return self._collection.count()
        if self._backend == "faiss" and self._faiss_index:
            return self._faiss_index.ntotal
        return 0

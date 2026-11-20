"""
Local Vector Retriever for Technical Specialist Support RAG.
Operates completely locally using term-frequency sparse embeddings and cosine similarity.
No external network, API keys, or paid embedding endpoints required.
"""

from __future__ import annotations

import math
import re
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from rag.knowledge_base import DocumentChunk, chunk_text, load_knowledge_base


def _tokenize(text: str) -> List[str]:
    """Extract normalized alphanumeric word tokens."""
    return re.findall(r"[a-z0-9]+", text.lower())


class LocalVectorRetriever:
    """
    In-memory semantic vector store for technical documentation retrieval.
    Indexes chunks and computes cosine similarity against search queries.
    """

    def __init__(self, kb_dir: Path | str, words_per_chunk: int = 80, overlap: int = 15):
        self.kb_dir = Path(kb_dir)
        self.words_per_chunk = words_per_chunk
        self.overlap = overlap
        self.chunks: List[DocumentChunk] = []
        self._doc_frequencies: Dict[str, int] = {}
        self._chunk_vectors: List[Dict[str, float]] = []
        self._vocab: set[str] = set()

        self._build_index()

    def _build_index(self) -> None:
        """Load documents, split into chunks, and compute TF-IDF index."""
        raw_docs = load_knowledge_base(self.kb_dir)
        self.chunks.clear()

        for doc in raw_docs:
            chunks = chunk_text(
                text=doc.content,
                doc_id=doc.doc_id,
                doc_title=doc.title,
                source_filename=doc.path.name,
                words_per_chunk=self.words_per_chunk,
                overlap=self.overlap,
            )
            self.chunks.extend(chunks)

        num_chunks = len(self.chunks)
        if num_chunks == 0:
            return

        # 1. Document frequency for IDF
        for chunk in self.chunks:
            tokens = set(_tokenize(chunk.text))
            for t in tokens:
                self._doc_frequencies[t] = self._doc_frequencies.get(t, 0) + 1
                self._vocab.add(t)

        # 2. Compute normalized TF-IDF vector for each chunk
        self._chunk_vectors.clear()
        for chunk in self.chunks:
            vec = self._vectorize_text(chunk.text, num_chunks)
            self._chunk_vectors.append(vec)

    def _vectorize_text(self, text: str, total_docs: int) -> Dict[str, float]:
        """Compute normalized TF-IDF vector dictionary."""
        tokens = _tokenize(text)
        if not tokens:
            return {}

        tf: Dict[str, float] = {}
        for t in tokens:
            tf[t] = tf.get(t, 0.0) + 1.0

        vec: Dict[str, float] = {}
        sq_sum = 0.0
        for t, count in tf.items():
            df = self._doc_frequencies.get(t, 1)
            idf = math.log((total_docs + 1) / (df + 1)) + 1.0
            val = (count / len(tokens)) * idf
            vec[t] = val
            sq_sum += val * val

        # L2 Normalization
        norm = math.sqrt(sq_sum)
        if norm > 0:
            for t in vec:
                vec[t] /= norm

        return vec

    def _cosine_similarity(self, vec_a: Dict[str, float], vec_b: Dict[str, float]) -> float:
        """Dot product of two unit-normalized sparse vectors."""
        if len(vec_a) > len(vec_b):
            vec_a, vec_b = vec_b, vec_a
        return sum(val * vec_b.get(term, 0.0) for term, val in vec_a.items())

    def search(
        self, query: str, top_k: int = 3, min_similarity: float = 0.20
    ) -> List[Tuple[DocumentChunk, float]]:
        """
        Search indexed knowledge base chunks by semantic cosine similarity.
        Filters out matches below min_similarity.
        """
        if not self.chunks or not query.strip():
            return []

        q_vec = self._vectorize_text(query, len(self.chunks))
        if not q_vec:
            return []

        scored: List[Tuple[DocumentChunk, float]] = []
        for chunk, chunk_vec in zip(self.chunks, self._chunk_vectors):
            sim = self._cosine_similarity(q_vec, chunk_vec)
            if sim >= min_similarity:
                scored.append((chunk, round(sim, 4)))

        # Sort descending by similarity score
        scored.sort(key=lambda item: item[1], reverse=True)
        return scored[:top_k]

    def get_context(
        self, query: str, top_k: int = 3, min_similarity: float = 0.20
    ) -> Tuple[str, List[str], bool]:
        """
        Returns:
            context_text: Formatted string of retrieved passages with citations.
            sources: List of source tags cited.
            sufficient_evidence: True if at least one relevant passage was found.
        """
        matches = self.search(query, top_k=top_k, min_similarity=min_similarity)
        if not matches:
            return (
                "INSUFFICIENT_EVIDENCE: No matching support documentation found in knowledge base.",
                [],
                False,
            )

        passages = []
        sources = []
        for chunk, score in matches:
            passages.append(f"{chunk.source} (relevance {score:.2f}):\n{chunk.text}")
            if chunk.source not in sources:
                sources.append(chunk.source)

        context_text = "\n\n---\n\n".join(passages)
        return context_text, sources, True

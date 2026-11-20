"""
Unit tests for Local RAG vector retriever and document chunking.
"""

import pytest
from pathlib import Path
from config import KB_DIR
from rag.knowledge_base import load_knowledge_base, chunk_text
from rag.retriever import LocalVectorRetriever


def test_knowledge_base_loading():
    docs = load_knowledge_base(KB_DIR)
    assert len(docs) >= 4
    doc_ids = [d.doc_id for d in docs]
    assert "troubleshooting_guide" in doc_ids
    assert "error_codes" in doc_ids
    assert "api_integration_guide" in doc_ids


def test_chunking_mechanics():
    sample_text = (
        "Section 1: First topic.\n\n"
        "This is paragraph one with enough words to verify chunking behavior and properties. "
        "It includes multiple sentences to test the sliding window chunker correctly.\n\n"
        "Section 2: Second topic."
    )
    chunks = chunk_text(sample_text, doc_id="test_doc", doc_title="Test Doc", source_filename="test.txt", words_per_chunk=15)
    assert len(chunks) >= 2
    assert all(c.source == "[test.txt]" for c in chunks)


def test_retriever_semantic_search():
    retriever = LocalVectorRetriever(kb_dir=KB_DIR)
    assert len(retriever.chunks) > 0

    # Query for gateway timeout
    matches = retriever.search("Gateway request timeout error code ERR-1001", top_k=2)
    assert len(matches) > 0
    top_chunk, score = matches[0]
    assert score > 0.20
    assert "1001" in top_chunk.text or "timeout" in top_chunk.text.lower()


def test_retriever_insufficient_evidence():
    retriever = LocalVectorRetriever(kb_dir=KB_DIR)
    # Query completely unrelated to support docs
    context, sources, sufficient = retriever.get_context(
        "Quantum molecular orbital wavefunction calculation with DFT",
        min_similarity=0.30,
    )
    assert sufficient is False
    assert "INSUFFICIENT_EVIDENCE" in context
    assert len(sources) == 0

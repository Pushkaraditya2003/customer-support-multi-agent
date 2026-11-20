"""
Knowledge Base Document Loader and Chunking Engine.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import List


@dataclass
class KnowledgeDocument:
    doc_id: str
    title: str
    content: str
    path: Path


@dataclass
class DocumentChunk:
    chunk_id: str
    doc_id: str
    doc_title: str
    text: str
    source: str


def chunk_text(
    text: str,
    doc_id: str,
    doc_title: str,
    source_filename: str,
    words_per_chunk: int = 70,
    overlap: int = 15,
) -> List[DocumentChunk]:
    """
    Split document content into semantically coherent overlapping chunks.
    Combines small headings with their accompanying paragraphs.
    """
    raw_paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
    merged_sections: List[str] = []
    current_section = ""

    for p in raw_paragraphs:
        # If paragraph is very short (like a heading '## Section 1: ...'), prepend/merge it
        if len(p.split()) < 12 and current_section:
            merged_sections.append(current_section)
            current_section = p
        elif len(p.split()) < 12:
            current_section = (current_section + " " + p).strip() if current_section else p
        else:
            current_section = (current_section + "\n" + p).strip() if current_section else p
            if len(current_section.split()) >= words_per_chunk:
                merged_sections.append(current_section)
                current_section = ""

    if current_section:
        merged_sections.append(current_section)

    chunks: List[DocumentChunk] = []
    chunk_idx = 0

    for sec in merged_sections:
        words = sec.split()
        if not words:
            continue

        if len(words) <= words_per_chunk + 10:
            chunk_idx += 1
            chunks.append(
                DocumentChunk(
                    chunk_id=f"{doc_id}-CHK-{chunk_idx:03d}",
                    doc_id=doc_id,
                    doc_title=doc_title,
                    text=" ".join(words),
                    source=f"[{source_filename}]",
                )
            )
        else:
            start = 0
            while start < len(words):
                end = min(start + words_per_chunk, len(words))
                sub_words = words[start:end]
                if sub_words:
                    chunk_idx += 1
                    chunks.append(
                        DocumentChunk(
                            chunk_id=f"{doc_id}-CHK-{chunk_idx:03d}",
                            doc_id=doc_id,
                            doc_title=doc_title,
                            text=" ".join(sub_words),
                            source=f"[{source_filename}]",
                        )
                    )
                if end >= len(words):
                    break
                start += max(1, words_per_chunk - overlap)

    return chunks


def load_knowledge_base(kb_dir: Path | str) -> List[KnowledgeDocument]:
    """Load all text documents from the knowledge_base directory."""
    path = Path(kb_dir)
    if not path.exists():
        raise FileNotFoundError(f"Knowledge base directory does not exist: {kb_dir}")

    docs: List[KnowledgeDocument] = []
    for f in sorted(path.glob("*.txt")):
        text = f.read_text(encoding="utf-8")
        title = f.stem.replace("_", " ").title()
        docs.append(
            KnowledgeDocument(
                doc_id=f.stem,
                title=title,
                content=text,
                path=f,
            )
        )
    return docs

from __future__ import annotations

import json
import os
import re
import time
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple

from pydantic import BaseModel, Field, ConfigDict


class EcoKGMaterializeInput(BaseModel):
    """Stable input schema to build a lightweight corpus from eco_knowledge_graph/data."""

    model_config = ConfigDict(extra="allow")

    output_dir: str = Field(..., description="Scenario output directory (e.g. outputs/<scenario_id>)")
    chunk_size: int = Field(default=600, ge=200, le=4000)
    chunk_overlap: int = Field(default=120, ge=0, le=1000)
    max_files: Optional[int] = Field(default=None, ge=1, le=100)


class EcoKGQueryInput(BaseModel):
    model_config = ConfigDict(extra="allow")

    output_dir: str = Field(..., description="Scenario output directory")
    query: str = Field(..., min_length=1, description="User query string")
    top_k: int = Field(default=6, ge=1, le=20)


def _repo_root() -> Path:
    # other_back_data/fdf/interface.py -> repo root is 2 levels up
    return Path(__file__).resolve().parents[2]


def _kg_data_dir() -> Path:
    return _repo_root() / "eco_knowledge_graph" / "data"


def _try_pdf_reader():
    try:
        from pypdf import PdfReader  # type: ignore
        return PdfReader
    except Exception:
        try:
            from PyPDF2 import PdfReader  # type: ignore
            return PdfReader
        except Exception:
            return None


def _extract_pdf_text(path: Path) -> List[Tuple[str, Dict[str, Any]]]:
    PdfReader = _try_pdf_reader()
    if PdfReader is None:
        return []

    out: List[Tuple[str, Dict[str, Any]]] = []
    try:
        reader = PdfReader(str(path))
        for i, page in enumerate(reader.pages):
            try:
                txt = (page.extract_text() or "").strip()
            except Exception:
                txt = ""
            if not txt:
                continue
            meta = {"source": path.name, "type": "pdf", "page": i + 1}
            out.append((txt, meta))
    except Exception:
        return []
    return out


def _extract_docx_text(path: Path) -> List[Tuple[str, Dict[str, Any]]]:
    out: List[Tuple[str, Dict[str, Any]]] = []
    try:
        from docx import Document  # type: ignore

        doc = Document(str(path))
        paras = [p.text.strip() for p in doc.paragraphs if p.text and p.text.strip()]
        txt = "\n".join(paras).strip()
        if txt:
            out.append((txt, {"source": path.name, "type": "docx", "page": None}))
    except Exception:
        return []
    return out


def _split_text(text: str, *, chunk_size: int, overlap: int) -> List[str]:
    text = (text or "").strip()
    if not text:
        return []
    # normalize whitespace
    text = re.sub(r"\s+", " ", text)

    if chunk_size <= 0:
        return [text]

    chunks = []
    i = 0
    n = len(text)
    step = max(1, chunk_size - overlap)
    while i < n:
        chunks.append(text[i : i + chunk_size])
        i += step
    return chunks


def materialize(payload: EcoKGMaterializeInput) -> Dict[str, Any]:
    """Build a lightweight local corpus cache.

    Output file:
      outputs/<scenario_id>/artifacts/eco_kg_corpus.jsonl

    MUST NOT raise.
    """
    print("[EcoKG] Starting materialize...")

    out_dir = Path(payload.output_dir)
    artifacts_dir = out_dir / "artifacts"
    artifacts_dir.mkdir(parents=True, exist_ok=True)

    data_dir = _kg_data_dir()
    if not data_dir.exists():
        print(f"[EcoKG] Error: data dir not found: {data_dir}")
        return {
            "ok": False,
            "source_id": "eco_knowledge_graph",
            "version": "0.1.0",
            "metrics": {},
            "artifacts": {},
            "inventory_files": [],
            "recommended_inputs": {},
            "error": {"type": "missing_dir", "message": f"KG data dir not found: {data_dir}"},
        }

    try:
        files = sorted([p for p in data_dir.iterdir() if p.suffix.lower() in {".pdf", ".docx"}])
        if payload.max_files:
            files = files[: payload.max_files]
        print(f"[EcoKG] Found {len(files)} files to process")

        corpus_path = artifacts_dir / "eco_kg_corpus.jsonl"

        total_chunks = 0
        doc_stats = []

        with corpus_path.open("w", encoding="utf-8") as f:
            for idx, p in enumerate(files):
                print(f"[EcoKG] Processing file {idx+1}/{len(files)}: {p.name}")
                if p.suffix.lower() == ".pdf":
                    parts = _extract_pdf_text(p)
                else:
                    parts = _extract_docx_text(p)

                doc_chunks = 0
                for txt, meta in parts:
                    chunks = _split_text(txt, chunk_size=payload.chunk_size, overlap=payload.chunk_overlap)
                    for idx, ch in enumerate(chunks):
                        rec = {
                            "text": ch,
                            "meta": {
                                **meta,
                                "chunk_index": idx,
                            },
                        }
                        f.write(json.dumps(rec, ensure_ascii=False) + "\n")
                        total_chunks += 1
                        doc_chunks += 1

                doc_stats.append({"file": p.name, "chunks": doc_chunks})

        print(f"[EcoKG] Completed: {len(files)} files, {total_chunks} chunks")
        return {
            "ok": True,
            "source_id": "eco_knowledge_graph",
            "version": "0.1.0",
            "metrics": {
                "files": [p.name for p in files],
                "file_count": len(files),
                "chunk_count": total_chunks,
                "chunk_size": payload.chunk_size,
                "chunk_overlap": payload.chunk_overlap,
            },
            "artifacts": {
                "corpus_path": str(corpus_path),
                "doc_stats": doc_stats,
            },
            "inventory_files": [str(p) for p in files],
            "recommended_inputs": {"jsonl_paths": [str(corpus_path)]},
            "error": None,
        }

    except Exception as e:
        print(f"[EcoKG] Materialize error: {e}")
        return {
            "ok": False,
            "source_id": "eco_knowledge_graph",
            "version": "0.1.0",
            "metrics": {},
            "artifacts": {},
            "inventory_files": [],
            "recommended_inputs": {},
            "error": {"type": "exception", "message": str(e)},
        }


@lru_cache(maxsize=4)
def _load_corpus(corpus_path: str) -> List[Dict[str, Any]]:
    items: List[Dict[str, Any]] = []
    p = Path(corpus_path)
    if not p.exists():
        return items
    with p.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                items.append(json.loads(line))
            except Exception:
                continue
    return items


@lru_cache(maxsize=2)
def _build_vector_index(corpus_path: str):
    items = _load_corpus(corpus_path)
    texts = [it.get("text", "") for it in items]

    # Use char n-grams for better CJK retrieval without jieba.
    from sklearn.feature_extraction.text import TfidfVectorizer  # type: ignore
    from sklearn.metrics.pairwise import cosine_similarity  # type: ignore

    vectorizer = TfidfVectorizer(analyzer="char", ngram_range=(2, 4), min_df=1)
    X = vectorizer.fit_transform(texts) if texts else None

    return items, vectorizer, X


def query(payload: EcoKGQueryInput) -> Dict[str, Any]:
    """Query the lightweight corpus and return top-k snippets.

    MUST NOT raise.
    """
    print(f"[EcoKG] Query: {payload.query[:50]}...")

    out_dir = Path(payload.output_dir)
    corpus_path = out_dir / "artifacts" / "eco_kg_corpus.jsonl"

    if not corpus_path.exists():
        print(f"[EcoKG] Error: corpus not found: {corpus_path}")
        return {
            "ok": False,
            "source_id": "eco_knowledge_graph",
            "version": "0.1.0",
            "metrics": {},
            "artifacts": {},
            "error": {
                "type": "missing_corpus",
                "message": f"Corpus cache not found. Run materialize() first: {corpus_path}",
            },
        }

    try:
        print("[EcoKG] Building vector index...")
        items, vectorizer, X = _build_vector_index(str(corpus_path))
        print(f"[EcoKG] Index built, {len(items)} items")
        if X is None or not items:
            return {
                "ok": True,
                "source_id": "eco_knowledge_graph",
                "version": "0.1.0",
                "metrics": {"query": payload.query, "top_k": payload.top_k, "hit_count": 0},
                "artifacts": {"snippets": []},
                "error": None,
            }

        from sklearn.metrics.pairwise import cosine_similarity  # type: ignore

        qv = vectorizer.transform([payload.query])
        sims = cosine_similarity(qv, X).flatten().tolist()

        # get top indices
        idxs = sorted(range(len(sims)), key=lambda i: sims[i], reverse=True)[: payload.top_k]
        snippets: List[Dict[str, Any]] = []
        for i in idxs:
            it = items[i]
            meta = it.get("meta") or {}
            snippets.append(
                {
                    "score": round(float(sims[i]), 6),
                    "text": it.get("text", "")[:800],
                    "source": meta.get("source"),
                    "type": meta.get("type"),
                    "page": meta.get("page"),
                    "chunk_index": meta.get("chunk_index"),
                }
            )

        print(f"[EcoKG] Query completed: {len(snippets)} snippets found")
        return {
            "ok": True,
            "source_id": "eco_knowledge_graph",
            "version": "0.1.0",
            "metrics": {"query": payload.query, "top_k": payload.top_k, "hit_count": len(snippets)},
            "artifacts": {"snippets": snippets, "corpus_path": str(corpus_path)},
            "error": None,
        }

    except Exception as e:
        print(f"[EcoKG] Query error: {e}")
        return {
            "ok": False,
            "source_id": "eco_knowledge_graph",
            "version": "0.1.0",
            "metrics": {},
            "artifacts": {},
            "error": {"type": "exception", "message": str(e)},
        }

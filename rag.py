"""极简 RAG：本地 md/txt 切块 + TF-IDF/BM25 词面检索（无 embedding）。"""
from __future__ import annotations

import math
import re
from collections import Counter
from pathlib import Path
from typing import Any

_JIEBA_AVAILABLE = False
try:
    import jieba

    _JIEBA_AVAILABLE = True
except ImportError:
    jieba = None  # type: ignore[assignment,misc]


def _tokenize_simple(text: str) -> list[str]:
    parts = re.findall(r"[a-zA-Z]{2,}|\d+|[\u4e00-\u9fff]", text.lower())
    return [p for p in parts if p]


def _tokenize(text: str) -> list[str]:
    if _JIEBA_AVAILABLE and jieba is not None:
        raw = jieba.lcut(text.lower())
        tokens: list[str] = []
        for t in raw:
            t = t.strip()
            if not t:
                continue
            if re.fullmatch(r"[a-zA-Z]{2,}|\d+", t):
                tokens.append(t)
            elif re.search(r"[\u4e00-\u9fff]", t):
                for ch in t:
                    if "\u4e00" <= ch <= "\u9fff":
                        tokens.append(ch)
        return tokens
    return _tokenize_simple(text)


def _chunk_text(text: str, chunk_size: int, overlap: int) -> list[str]:
    if chunk_size <= 0:
        return [text]
    chunks: list[str] = []
    start = 0
    n = len(text)
    while start < n:
        end = min(start + chunk_size, n)
        chunks.append(text[start:end].strip())
        if end >= n:
            break
        start = max(0, end - overlap)
    return [c for c in chunks if c]


def load_corpus(root: Path, chunk_size: int, overlap: int) -> list[dict[str, Any]]:
    if not root.is_dir():
        return []
    chunks: list[dict[str, Any]] = []
    for path in sorted(root.rglob("*")):
        if not path.is_file():
            continue
        if path.suffix.lower() not in (".md", ".txt", ".markdown"):
            continue
        raw = path.read_text(encoding="utf-8", errors="replace")
        rel = str(path.relative_to(root))
        for i, piece in enumerate(_chunk_text(raw, chunk_size, overlap)):
            chunks.append({"source": rel, "chunk_index": i, "text": piece})
    return chunks


def score_chunk(
    query: str,
    chunk_text: str,
    idf: dict[str, float] | None = None,
    *,
    avg_dl: float = 1.0,
    k1: float = 1.5,
    b: float = 0.75,
) -> float:
    """TF-IDF 或 BM25 风格打分（有 idf 时用 BM25）。"""
    q_tokens = _tokenize(query)
    if not q_tokens:
        return 0.0
    c_tokens = _tokenize(chunk_text)
    if not c_tokens:
        return 0.0
    if idf is None:
        inter = set(q_tokens) & set(c_tokens)
        return len(inter) / len(set(q_tokens))

    cf = Counter(c_tokens)
    dl = len(c_tokens)
    score = 0.0
    for t in set(q_tokens):
        if t not in cf:
            continue
        tf = cf[t]
        idf_val = idf.get(t, 0.0)
        bm25_tf = (tf * (k1 + 1)) / (tf + k1 * (1 - b + b * dl / avg_dl))
        score += idf_val * bm25_tf
    return score


def _build_idf(chunks: list[dict[str, Any]]) -> dict[str, float]:
    n = len(chunks) or 1
    df: dict[str, int] = {}
    for ch in chunks:
        for t in set(_tokenize(ch["text"])):
            df[t] = df.get(t, 0) + 1
    return {t: math.log((n + 1) / (count + 1)) + 1.0 for t, count in df.items()}


def _avg_doc_len(chunks: list[dict[str, Any]]) -> float:
    if not chunks:
        return 1.0
    total = sum(len(_tokenize(ch["text"])) for ch in chunks)
    return total / len(chunks) or 1.0


class KnowledgeIndex:
    """惰性加载知识库切块。"""

    def __init__(self, root: Path, chunk_size: int, overlap: int) -> None:
        self._root = root
        self._chunk_size = chunk_size
        self._overlap = overlap
        self._chunks: list[dict[str, Any]] | None = None
        self._idf: dict[str, float] | None = None
        self._avg_dl: float = 1.0

    def _ensure(self) -> None:
        if self._chunks is None:
            self._chunks = load_corpus(self._root, self._chunk_size, self._overlap)
            self._idf = _build_idf(self._chunks)
            self._avg_dl = _avg_doc_len(self._chunks)

    def search(self, query: str, top_k: int) -> dict[str, Any]:
        self._ensure()
        assert self._chunks is not None
        assert self._idf is not None
        if not self._chunks:
            return {
                "results": [],
                "hits": [],
                "note": f"知识库目录为空或不存在: {self._root}（可放入 .md / .txt）",
            }
        scored: list[tuple[float, dict[str, Any]]] = []
        for ch in self._chunks:
            s = score_chunk(query, ch["text"], self._idf, avg_dl=self._avg_dl)
            if s > 0:
                scored.append((s, ch))
        scored.sort(key=lambda x: -x[0])
        top = scored[:top_k]
        results = [
            {
                "source": ch["source"],
                "chunk_index": ch["chunk_index"],
                "score": round(s, 4),
                "text": ch["text"][:2000],
            }
            for s, ch in top
        ]
        if not results:
            for ch in self._chunks[:top_k]:
                results.append(
                    {
                        "source": ch["source"],
                        "chunk_index": ch["chunk_index"],
                        "score": 0.0,
                        "text": ch["text"][:2000],
                    }
                )
            return {
                "results": results,
                "hits": results,
                "note": "查询词与知识库词面重合度低，以下为库内前几条片段供参考。",
            }
        return {"results": results, "hits": results}

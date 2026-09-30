"""RAG: text cleaning -> chunking -> embeddings -> FAISS vector index -> retrieval.
One in-memory FAISS index per uploaded report (cached by content hash)."""
import hashlib
import re
import threading
from collections import OrderedDict
from typing import Dict, List

import config  # noqa: F401  (sets HF_HOME first)

_embedder = None
_embed_lock = threading.Lock()
_cache: "OrderedDict[str, ReportIndex]" = OrderedDict()
_cache_lock = threading.Lock()
MAX_CACHED_REPORTS = 20


def clean_text(text: str) -> str:
    text = text.replace("\r", "\n").replace("\u00a0", " ")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n[ \t]+", "\n", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def _split_long(paragraph: str, max_chars: int) -> List[str]:
    sentences = re.split(r"(?<=[.;])\s+", paragraph)
    out, cur = [], ""
    for s in sentences:
        if cur and len(cur) + 1 + len(s) > max_chars:
            out.append(cur)
            cur = s
        else:
            cur = f"{cur} {s}".strip()
    if cur:
        out.append(cur)
    return out


def chunk_text(text: str, max_chars: int = 500) -> List[str]:
    """Split on blank lines and ALL-CAPS section headings (e.g. 'IMPRESSION:'),
    then pack small pieces together up to max_chars."""
    paragraphs = [
        p.strip()
        for p in re.split(r"\n\s*\n|\n(?=[A-Z][A-Z ,&/()\-]{3,}:)", text)
        if p.strip()
    ]
    units: List[str] = []
    for p in paragraphs:
        units.extend([p] if len(p) <= max_chars else _split_long(p, max_chars))
    chunks, buf = [], ""
    for u in units:
        if buf and len(buf) + 1 + len(u) > max_chars:
            chunks.append(buf)
            buf = u
        else:
            buf = f"{buf}\n{u}" if buf else u
    if buf:
        chunks.append(buf)
    return chunks


def embed(texts: List[str]):
    global _embedder
    with _embed_lock:
        if _embedder is None:
            from sentence_transformers import SentenceTransformer
            _embedder = SentenceTransformer(config.EMBED_MODEL, device=config.get_device())
    import numpy as np
    vecs = _embedder.encode(texts, normalize_embeddings=True, show_progress_bar=False)
    return np.asarray(vecs, dtype="float32")


class ReportIndex:
    def __init__(self, text: str):
        import faiss
        self.chunks = chunk_text(clean_text(text))
        vectors = embed(["passage: " + c for c in self.chunks])
        self.index = faiss.IndexFlatIP(vectors.shape[1])
        self.index.add(vectors)

    def search(self, query: str, k: int) -> List[Dict]:
        if not self.chunks:
            return []
        qv = embed(["query: " + query])
        scores, ids = self.index.search(qv, min(k, len(self.chunks)))
        hits = [
            {"id": int(i), "score": float(s), "text": self.chunks[int(i)]}
            for i, s in zip(ids[0], scores[0]) if i >= 0
        ]
        return sorted(hits, key=lambda h: h["id"])  # keep original report order


def get_index(report_text: str) -> ReportIndex:
    key = hashlib.sha256(report_text.encode("utf-8")).hexdigest()
    with _cache_lock:
        if key in _cache:
            _cache.move_to_end(key)
            return _cache[key]
    idx = ReportIndex(report_text)
    with _cache_lock:
        _cache[key] = idx
        while len(_cache) > MAX_CACHED_REPORTS:
            _cache.popitem(last=False)
    return idx


def retrieve(report_text: str, query: str, k: int = None) -> List[Dict]:
    return get_index(report_text).search(query, k or config.TOP_K)
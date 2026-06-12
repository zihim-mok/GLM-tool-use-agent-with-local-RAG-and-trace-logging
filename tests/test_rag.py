"""RAG 打分测试。"""
from rag import score_chunk, _build_idf, load_corpus
from pathlib import Path


def test_score_chunk_overlap():
    s = score_chunk("复利 计算", "复利是把利息并入本金再计息")
    assert s > 0


def test_score_chunk_with_idf():
    root = Path(__file__).resolve().parent.parent / "knowledge"
    chunks = load_corpus(root, 400, 80)
    if not chunks:
        return
    idf = _build_idf(chunks)
    s = score_chunk("复利", chunks[0]["text"], idf)
    assert s >= 0


def test_score_chunk_no_match():
    s = score_chunk("", "some text")
    assert s == 0.0

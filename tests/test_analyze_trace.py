"""analyze_trace 冒烟测试。"""
from pathlib import Path

from analyze_trace import analyze, mermaid_diagram, html_report


def test_analyze_sample_trace():
    path = Path(__file__).resolve().parent.parent / "docs" / "trace_sample.jsonl"
    text = analyze(path)
    assert "trace_id" in text
    assert "user_message" in text or "事件数" in text


def test_mermaid_output():
    path = Path(__file__).resolve().parent.parent / "docs" / "trace_sample.jsonl"
    md = mermaid_diagram(path)
    assert "sequenceDiagram" in md
    assert "User" in md


def test_html_report():
    path = Path(__file__).resolve().parent.parent / "docs" / "trace_sample.jsonl"
    html = html_report(path)
    assert "<html" in html.lower()
    assert "Trace Report" in html

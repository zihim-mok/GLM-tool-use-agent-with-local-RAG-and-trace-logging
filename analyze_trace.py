"""
解析 trace JSONL，输出 Agent 链路时间线与统计（用于调试与简历演示）。

用法:
  python analyze_trace.py logs/<trace_id>.jsonl
  python analyze_trace.py docs/trace_sample.jsonl --mermaid
  python analyze_trace.py docs/trace_sample.jsonl --html report.html
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


def _load_rows(path: Path) -> list[dict]:
    rows: list[dict] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line:
            rows.append(json.loads(line))
    return rows


def analyze(path: Path) -> str:
    rows = _load_rows(path)
    if not rows:
        return "空日志文件"

    lines: list[str] = []
    trace_id = rows[0].get("trace_id", "?")
    lines.append(f"trace_id: {trace_id}")
    lines.append(f"事件数: {len(rows)}\n")

    tool_ms = 0
    tool_calls = 0
    llm_rounds = 0

    for i, row in enumerate(rows, 1):
        event = row.get("event", "?")
        ts = row.get("ts", "")[:19]
        extra = {k: v for k, v in row.items() if k not in ("ts", "trace_id", "event")}
        preview = ""
        if event == "tool_result" and "duration_ms" in extra:
            tool_ms += int(extra["duration_ms"])
            tool_calls += 1
            preview = f" {extra.get('name')} {extra['duration_ms']}ms"
        elif event == "llm_response":
            llm_rounds += 1
            preview = f" tool_calls={extra.get('has_tool_calls')}"
        elif event == "user_message":
            preview = f" {extra.get('preview', '')[:40]}"
        elif event == "assistant_final":
            preview = f" {extra.get('preview', '')[:40]}"
        lines.append(f"{i:02d} {ts}  {event}{preview}")

    lines.append(
        f"\n汇总: LLM 响应轮次={llm_rounds} 工具调用={tool_calls} "
        f"工具总耗时={tool_ms}ms"
    )
    return "\n".join(lines)


def mermaid_diagram(path: Path) -> str:
    rows = _load_rows(path)
    if not rows:
        return "sequenceDiagram\n  Note over User: empty trace"

    parts = ["sequenceDiagram", "  participant User", "  participant LLM", "  participant Tools"]
    for row in rows:
        event = row.get("event", "")
        if event == "user_message":
            preview = str(row.get("preview", ""))[:30].replace('"', "'")
            parts.append(f"  User->>LLM: {preview}")
        elif event == "llm_response":
            if row.get("has_tool_calls"):
                parts.append("  LLM->>Tools: tool_calls")
            else:
                parts.append("  LLM->>User: response")
        elif event == "tool_call":
            name = row.get("name", "?")
            parts.append(f"  Tools->>Tools: {name}")
        elif event == "tool_result":
            name = row.get("name", "?")
            ms = row.get("duration_ms", 0)
            parts.append(f"  Tools-->>LLM: {name} ({ms}ms)")
        elif event == "assistant_final":
            parts.append("  LLM->>User: final")
    return "\n".join(parts)


def html_report(path: Path) -> str:
    rows = _load_rows(path)
    trace_id = rows[0].get("trace_id", "?") if rows else "?"
    tool_ms_max = max(
        (int(r.get("duration_ms", 0)) for r in rows if r.get("event") == "tool_result"),
        default=1,
    ) or 1

    event_rows: list[str] = []
    for row in rows:
        event = row.get("event", "?")
        ts = row.get("ts", "")[:19]
        detail = ""
        bar = ""
        if event == "tool_result":
            ms = int(row.get("duration_ms", 0))
            pct = min(100, int(ms / tool_ms_max * 100))
            bar = f'<div class="bar" style="width:{pct}%"></div>'
            detail = f"{row.get('name')} {ms}ms"
        elif event == "user_message":
            detail = str(row.get("preview", ""))[:60]
        elif event == "llm_response":
            detail = f"tool_calls={row.get('has_tool_calls')}"
        elif event == "tool_call":
            detail = str(row.get("name", ""))
        event_rows.append(
            f"<tr><td>{ts}</td><td>{event}</td><td>{detail}</td>"
            f"<td class='timing'>{bar}</td></tr>"
        )

    return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8"/>
<title>Trace {trace_id}</title>
<style>
body {{ font-family: system-ui, sans-serif; margin: 2rem; background: #0f172a; color: #e2e8f0; }}
h1 {{ font-size: 1.2rem; }}
table {{ border-collapse: collapse; width: 100%; }}
th, td {{ border: 1px solid #334155; padding: 0.4rem 0.6rem; text-align: left; }}
th {{ background: #1e293b; }}
.timing {{ width: 30%; }}
.bar {{ height: 8px; background: #38bdf8; border-radius: 4px; }}
</style>
</head>
<body>
<h1>Trace Report: {trace_id}</h1>
<p>Events: {len(rows)}</p>
<table>
<thead><tr><th>Time</th><th>Event</th><th>Detail</th><th>Timing</th></tr></thead>
<tbody>
{"".join(event_rows)}
</tbody>
</table>
</body>
</html>"""


def main() -> None:
    parser = argparse.ArgumentParser(description="分析 Agent trace JSONL")
    parser.add_argument("path", type=Path, help="JSONL 文件路径")
    parser.add_argument("--mermaid", action="store_true", help="输出 Mermaid 时序图")
    parser.add_argument("--html", type=Path, nargs="?", const=Path("trace_report.html"), help="输出 HTML 报告")
    args = parser.parse_args()

    if not args.path.is_file():
        raise SystemExit(f"文件不存在: {args.path}")

    if args.mermaid:
        print(mermaid_diagram(args.path))
    elif args.html is not None:
        out = args.html
        out.write_text(html_report(args.path), encoding="utf-8")
        print(f"HTML 报告已写入: {out}")
    else:
        print(analyze(args.path))


if __name__ == "__main__":
    main()

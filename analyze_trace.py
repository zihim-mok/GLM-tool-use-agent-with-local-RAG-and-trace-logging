"""
解析 trace JSONL，输出 Agent 链路时间线与统计（用于调试与简历演示）。

用法:
  python analyze_trace.py logs/<trace_id>.jsonl
"""
from __future__ import annotations

import json
import sys
from pathlib import Path


def analyze(path: Path) -> None:
    rows: list[dict] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line:
            rows.append(json.loads(line))

    if not rows:
        print("空日志文件")
        return

    trace_id = rows[0].get("trace_id", "?")
    print(f"trace_id: {trace_id}")
    print(f"事件数: {len(rows)}\n")

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
        print(f"{i:02d} {ts}  {event}{preview}")

    print(
        f"\n汇总: LLM 响应轮次={llm_rounds} 工具调用={tool_calls} "
        f"工具总耗时={tool_ms}ms"
    )


if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit("用法: python analyze_trace.py <path-to.jsonl>")
    analyze(Path(sys.argv[1]))

"""观测：trace_id + 控制台日志 + 可选 JSONL 落盘。"""
from __future__ import annotations

import json
import logging
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def setup_logging() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        datefmt="%H:%M:%S",
    )


class TraceSession:
    def __init__(self, trace_id: str, jsonl_file: Path | None) -> None:
        self.trace_id = trace_id
        self.jsonl_file = jsonl_file
        self._log = logging.getLogger("agent.trace")
        self.stats: dict[str, int] = {
            "llm_rounds": 0,
            "tool_calls": 0,
            "tool_ms_total": 0,
            "user_turns": 0,
        }

    @classmethod
    def new(cls, jsonl_dir: Path | None) -> TraceSession:
        tid = str(uuid.uuid4())
        jf: Path | None = None
        if jsonl_dir is not None:
            jsonl_dir.mkdir(parents=True, exist_ok=True)
            jf = jsonl_dir / f"{tid}.jsonl"
        return cls(tid, jf)

    def emit(self, event: str, **data: Any) -> None:
        row: dict[str, Any] = {
            "ts": datetime.now(timezone.utc).isoformat(),
            "trace_id": self.trace_id,
            "event": event,
            **data,
        }
        msg = json.dumps(row, ensure_ascii=False)
        self._log.info("%s", msg)
        if self.jsonl_file is not None:
            with self.jsonl_file.open("a", encoding="utf-8") as f:
                f.write(msg + "\n")

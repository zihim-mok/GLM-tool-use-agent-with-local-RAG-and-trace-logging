"""从环境变量读取配置（需先 load_env_file）。"""
from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from env_loader import strip_invisible_unicode


def _root() -> Path:
    return Path(__file__).resolve().parent


@dataclass(frozen=True)
class AppConfig:
    zhipu_api_key: str
    glm_model: str
    max_tool_rounds: int
    max_context_messages: int
    knowledge_dir: Path
    rag_top_k: int
    rag_chunk_size: int
    rag_chunk_overlap: int
    trace_jsonl_dir: Path | None

    @classmethod
    def from_env(cls) -> AppConfig:
        key = strip_invisible_unicode(os.getenv("ZHIPU_API_KEY", "").strip().strip('"').strip("'"))
        trace_dir_raw = os.getenv("TRACE_JSONL_DIR", "logs").strip()
        trace_path = _root() / trace_dir_raw if trace_dir_raw and trace_dir_raw.lower() not in ("0", "false", "off", "no") else None

        kd = os.getenv("KNOWLEDGE_DIR", "knowledge").strip()
        knowledge_path = Path(kd) if Path(kd).is_absolute() else _root() / kd

        return cls(
            zhipu_api_key=key,
            glm_model=os.getenv("GLM_MODEL", "glm-4-flash").strip(),
            max_tool_rounds=max(1, int(os.getenv("MAX_TOOL_ROUNDS", "8"))),
            max_context_messages=max(4, int(os.getenv("MAX_CONTEXT_MESSAGES", "24"))),
            knowledge_dir=knowledge_path,
            rag_top_k=max(1, int(os.getenv("RAG_TOP_K", "3"))),
            rag_chunk_size=max(100, int(os.getenv("RAG_CHUNK_SIZE", "400"))),
            rag_chunk_overlap=max(0, int(os.getenv("RAG_CHUNK_OVERLAP", "80"))),
            trace_jsonl_dir=trace_path,
        )

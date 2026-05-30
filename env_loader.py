"""加载 .env 到 os.environ（无第三方依赖）。"""
from __future__ import annotations

import os
from pathlib import Path


def strip_invisible_unicode(s: str) -> str:
    for ch in ("\ufeff", "\u200b", "\u200c", "\u200d", "\u2060"):
        s = s.replace(ch, "")
    s = s.replace("\u00a0", " ").strip()
    return s


def load_env_file(path: Path | None = None, *, override: bool = True) -> None:
    env_path = path or (Path(__file__).resolve().parent / ".env")
    if not env_path.is_file():
        return
    for raw in env_path.read_text(encoding="utf-8-sig").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, val = line.partition("=")
        key = key.strip()
        val = strip_invisible_unicode(val.strip().strip('"').strip("'"))
        if key and (override or key not in os.environ):
            os.environ[key] = val

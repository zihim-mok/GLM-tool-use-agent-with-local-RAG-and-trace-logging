"""行情查询 TTL 缓存：内存 + 可选文件持久化。"""
from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any

_MEMORY: dict[str, tuple[float, dict[str, Any]]] = {}
_DEFAULT_TTL = 600


def _cache_key(symbol: str, date: str | None) -> str:
    d = date or "__latest__"
    return f"{symbol.strip().upper()}|{d}"


def _file_path(cache_dir: Path) -> Path:
    return cache_dir / "quote_cache.json"


def _load_file(cache_dir: Path) -> dict[str, Any]:
    path = _file_path(cache_dir)
    if not path.is_file():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {}


def _save_file(cache_dir: Path, data: dict[str, Any]) -> None:
    cache_dir.mkdir(parents=True, exist_ok=True)
    _file_path(cache_dir).write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")


def get_cached(
    symbol: str,
    date: str | None,
    ttl_seconds: int,
    cache_dir: Path | None = None,
) -> dict[str, Any] | None:
    key = _cache_key(symbol, date)
    now = time.time()
    entry = _MEMORY.get(key)
    if entry and now - entry[0] < ttl_seconds:
        result = dict(entry[1])
        result["cached"] = True
        return result
    if cache_dir is not None:
        file_data = _load_file(cache_dir)
        fe = file_data.get(key)
        if fe and isinstance(fe, dict):
            ts = float(fe.get("_ts", 0))
            if now - ts < ttl_seconds and "data" in fe:
                result = dict(fe["data"])
                result["cached"] = True
                _MEMORY[key] = (ts, fe["data"])
                return result
    return None


def set_cached(
    symbol: str,
    date: str | None,
    data: dict[str, Any],
    cache_dir: Path | None = None,
) -> None:
    if "error" in data:
        return
    key = _cache_key(symbol, date)
    clean = {k: v for k, v in data.items() if k != "cached"}
    now = time.time()
    _MEMORY[key] = (now, clean)
    if cache_dir is not None:
        file_data = _load_file(cache_dir)
        file_data[key] = {"_ts": now, "data": clean}
        _save_file(cache_dir, file_data)


def clear_cache() -> None:
    _MEMORY.clear()

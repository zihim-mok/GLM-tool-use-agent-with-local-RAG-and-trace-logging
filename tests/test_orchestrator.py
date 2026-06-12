"""orchestrator 工具去重测试。"""
from orchestrator import resolve_tool_result, tool_call_cache_key


def test_tool_call_cache_key_stable():
    k1 = tool_call_cache_key("lookup_quote", {"symbol": "600519"})
    k2 = tool_call_cache_key("lookup_quote", {"symbol": "600519"})
    assert k1 == k2


def test_turn_dedupe_skips_second_dispatch():
    calls: list[tuple[str, dict]] = []

    def dispatch(name: str, args: dict) -> dict:
        calls.append((name, args))
        return {"close": 1.0}

    turn_cache: dict[str, dict] = {}
    r1 = resolve_tool_result("lookup_quote", {"symbol": "600519"}, dispatch, turn_cache=turn_cache)
    r2 = resolve_tool_result("lookup_quote", {"symbol": "600519"}, dispatch, turn_cache=turn_cache)
    assert len(calls) == 1
    assert r2.get("deduped") is True
    assert r2.get("dedupe_scope") == "turn"


def test_session_dedupe_for_lookup_quote():
    calls: list[tuple[str, dict]] = []

    def dispatch(name: str, args: dict) -> dict:
        calls.append((name, args))
        return {"close": 2.0}

    turn_cache: dict[str, dict] = {}
    session_cache: dict[str, dict] = {}
    resolve_tool_result(
        "lookup_quote",
        {"symbol": "600519"},
        dispatch,
        turn_cache=turn_cache,
        dedupe_cache=session_cache,
    )
    turn_cache.clear()
    r2 = resolve_tool_result(
        "lookup_quote",
        {"symbol": "600519"},
        dispatch,
        turn_cache=turn_cache,
        dedupe_cache=session_cache,
    )
    assert len(calls) == 1
    assert r2.get("deduped") is True
    assert r2.get("dedupe_scope") == "session"

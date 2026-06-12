"""工具注册中心测试。"""
import tools  # noqa: F401 — 触发 @register_tool 注册

from tool_registry import tool_definitions, get_handler, registered_tool_names


def test_all_tools_registered():
    names = registered_tool_names()
    assert "compound_interest" in names
    assert "lookup_quote" in names
    assert "sharpe_ratio" in names
    assert len(names) >= 17


def test_tool_definitions_schema():
    defs = tool_definitions()
    assert len(defs) >= 17
    for d in defs:
        assert d["type"] == "function"
        assert "name" in d["function"]


def test_handler_lookup():
    h = get_handler("cagr")
    assert h is not None
    r = h(100, 150, 3)
    assert "cagr_pct" in r

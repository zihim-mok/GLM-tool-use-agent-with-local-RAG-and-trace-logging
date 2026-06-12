"""为工具返回补充 disclaimer、data_as_of、source 等结构化元数据。"""
from __future__ import annotations

from datetime import datetime
from typing import Any

_FINANCE_DISCLAIMER = "计算结果仅供学习演示，不构成投资建议。"
_MARKET_DISCLAIMER = "行情数据仅供参考，不构成投资建议；实盘请以交易所或权威数据源为准。"


def enrich_tool_result(
    result: dict[str, Any],
    *,
    category: str = "general",
    source: str | None = None,
    data_as_of: str | None = None,
) -> dict[str, Any]:
    """在工具结果上附加元数据，不覆盖已有字段。"""
    if "error" in result:
        return result
    out = dict(result)
    if category == "finance":
        out.setdefault("disclaimer", _FINANCE_DISCLAIMER)
    elif category == "market":
        out.setdefault("disclaimer", _MARKET_DISCLAIMER)
    if source and "source" not in out:
        out["source"] = source
    if data_as_of:
        out.setdefault("data_as_of", data_as_of)
    elif category == "market" and "data_as_of" not in out:
        trade = out.get("trade_date") or out.get("date")
        if trade:
            out["data_as_of"] = str(trade)
    out.setdefault("retrieved_at", datetime.now().isoformat(timespec="seconds"))
    return out

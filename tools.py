"""工具 schema + 本地实现 + 统一 dispatch。"""
from __future__ import annotations

import json
from datetime import datetime
from typing import Any, Callable

from config import AppConfig
from finance_tools import (
    cagr,
    compound_interest,
    inflation_adjust,
    loan_monthly_payment,
    pct_change,
    rule_of_72,
    savings_goal_monthly,
    simple_interest,
)
from market_data import (
    compare_symbols_live,
    fetch_fx_usdcny,
    fetch_stock_history,
    lookup_quote_with_fallback,
    portfolio_summary_live,
)
from rag import KnowledgeIndex


def tool_definitions() -> list[dict[str, Any]]:
    return [
        {
            "type": "function",
            "function": {
                "name": "get_current_time",
                "description": "返回当前本地日期与时间（本机时区）。",
                "parameters": {"type": "object", "properties": {}, "required": []},
            },
        },
        {
            "type": "function",
            "function": {
                "name": "calculate",
                "description": "计算仅含数字与 + - * / ( ) 和空格的数学表达式。",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "expression": {"type": "string", "description": "数学表达式"},
                    },
                    "required": ["expression"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "search_knowledge",
                "description": "从本地知识库检索金融概念、产品说明、工具使用说明等文本片段。",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "query": {"type": "string", "description": "检索关键词或问句"},
                    },
                    "required": ["query"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "compound_interest",
                "description": "复利终值计算。annual_rate_pct 为年化百分比，如 3 表示 3%。",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "principal": {"type": "number", "description": "本金"},
                        "annual_rate_pct": {"type": "number", "description": "年化利率(%)"},
                        "years": {"type": "number", "description": "年数"},
                        "compounds_per_year": {"type": "integer", "description": "每年复利次数，默认 12"},
                    },
                    "required": ["principal", "annual_rate_pct", "years"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "simple_interest",
                "description": "单利终值计算。",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "principal": {"type": "number"},
                        "annual_rate_pct": {"type": "number"},
                        "years": {"type": "number"},
                    },
                    "required": ["principal", "annual_rate_pct", "years"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "loan_monthly_payment",
                "description": "等额本息房贷/贷款月供估算。",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "principal": {"type": "number", "description": "贷款本金"},
                        "annual_rate_pct": {"type": "number", "description": "年化利率(%)"},
                        "months": {"type": "integer", "description": "还款月数"},
                    },
                    "required": ["principal", "annual_rate_pct", "months"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "savings_goal_monthly",
                "description": "为达到目标金额，估算每月定投金额（复利近似）。",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "target_amount": {"type": "number"},
                        "annual_rate_pct": {"type": "number"},
                        "months": {"type": "integer"},
                    },
                    "required": ["target_amount", "annual_rate_pct", "months"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "pct_change",
                "description": "计算两数值之间的涨跌额与涨跌幅(%)",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "old_value": {"type": "number"},
                        "new_value": {"type": "number"},
                    },
                    "required": ["old_value", "new_value"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "cagr",
                "description": "复合年增长率 CAGR (%)",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "begin_value": {"type": "number"},
                        "end_value": {"type": "number"},
                        "years": {"type": "number"},
                    },
                    "required": ["begin_value", "end_value", "years"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "rule_of_72",
                "description": "72 法则：估算本金翻倍所需年数",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "annual_rate_pct": {"type": "number", "description": "年化收益率(%)"},
                    },
                    "required": ["annual_rate_pct"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "inflation_adjust",
                "description": "按通胀率折现名义金额的购买力（粗算）",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "nominal_amount": {"type": "number"},
                        "annual_inflation_pct": {"type": "number"},
                        "years": {"type": "number"},
                    },
                    "required": ["nominal_amount", "annual_inflation_pct", "years"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "lookup_quote",
                "description": (
                    "查询股票/指数收盘价，优先联网：A 股东方财富失败后接 akshare，美股 Stooq/yfinance。"
                    "查最新价不要传 date。symbol 如 600519、000636、AAPL；指数如 sh000001。"
                ),
                "parameters": {
                    "type": "object",
                    "properties": {
                        "symbol": {"type": "string"},
                        "date": {
                            "type": "string",
                            "description": "可选 YYYY-MM-DD。查最新价时不要传；禁止填多年前日期",
                        },
                    },
                    "required": ["symbol"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "compare_symbols",
                "description": "对比两只标的最近收盘价与价格比",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "symbol_a": {"type": "string"},
                        "symbol_b": {"type": "string"},
                    },
                    "required": ["symbol_a", "symbol_b"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "portfolio_summary",
                "description": "根据示例持仓文件与联网行情，汇总组合市值与盈亏",
                "parameters": {"type": "object", "properties": {}, "required": []},
            },
        },
        {
            "type": "function",
            "function": {
                "name": "get_stock_history",
                "description": "获取近 N 日收盘价历史（联网，A 股 akshare / 美股 yfinance）",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "symbol": {"type": "string"},
                        "days": {"type": "integer", "description": "天数，5-120，默认 30"},
                    },
                    "required": ["symbol"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "get_fx_usdcny",
                "description": "查询美元兑人民币汇率（akshare 中行汇价，仅供参考）",
                "parameters": {"type": "object", "properties": {}, "required": []},
            },
        },
    ]


def _num(args: dict[str, Any], key: str, default: float = 0.0) -> float:
    try:
        return float(args.get(key, default))
    except (TypeError, ValueError):
        return default


def _int(args: dict[str, Any], key: str, default: int = 0) -> int:
    try:
        return int(args.get(key, default))
    except (TypeError, ValueError):
        return default


def _tool_get_current_time() -> dict[str, Any]:
    return {
        "iso": datetime.now().isoformat(timespec="seconds"),
        "note": "时间为运行本脚本的机器本地时间。",
    }


def _tool_calculate(expression: str) -> dict[str, Any]:
    allowed = set("0123456789+-*/().")
    if not expression or not all(c in allowed or c.isspace() for c in expression):
        return {"error": "表达式仅允许数字与 + - * / ( ) 及空格。"}
    try:
        value = eval(expression, {"__builtins__": {}}, {})
    except Exception as e:
        return {"error": f"计算失败: {e}"}
    return {"expression": expression.strip(), "result": value}


def make_dispatch(config: AppConfig, index: KnowledgeIndex) -> Callable[[str, dict[str, Any]], dict[str, Any]]:
    def dispatch(name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        if name == "get_current_time":
            return _tool_get_current_time()
        if name == "calculate":
            return _tool_calculate(str(arguments.get("expression", "")))
        if name == "search_knowledge":
            q = str(arguments.get("query", "")).strip()
            if not q:
                return {"error": "query 不能为空"}
            return index.search(q, config.rag_top_k)
        if name == "compound_interest":
            return compound_interest(
                _num(arguments, "principal"),
                _num(arguments, "annual_rate_pct"),
                _num(arguments, "years"),
                _int(arguments, "compounds_per_year", 12) or 12,
            )
        if name == "simple_interest":
            return simple_interest(
                _num(arguments, "principal"),
                _num(arguments, "annual_rate_pct"),
                _num(arguments, "years"),
            )
        if name == "loan_monthly_payment":
            return loan_monthly_payment(
                _num(arguments, "principal"),
                _num(arguments, "annual_rate_pct"),
                _int(arguments, "months"),
            )
        if name == "savings_goal_monthly":
            return savings_goal_monthly(
                _num(arguments, "target_amount"),
                _num(arguments, "annual_rate_pct"),
                _int(arguments, "months"),
            )
        if name == "pct_change":
            return pct_change(_num(arguments, "old_value"), _num(arguments, "new_value"))
        if name == "cagr":
            return cagr(_num(arguments, "begin_value"), _num(arguments, "end_value"), _num(arguments, "years"))
        if name == "rule_of_72":
            return rule_of_72(_num(arguments, "annual_rate_pct"))
        if name == "inflation_adjust":
            return inflation_adjust(
                _num(arguments, "nominal_amount"),
                _num(arguments, "annual_inflation_pct"),
                _num(arguments, "years"),
            )
        if name == "lookup_quote":
            sym = str(arguments.get("symbol", "")).strip()
            raw_date = str(arguments.get("date", "")).strip() or None
            return lookup_quote_with_fallback(
                sym, config.quotes_csv, raw_date, use_live=config.use_live_market_data
            )
        if name == "compare_symbols":
            return compare_symbols_live(
                str(arguments.get("symbol_a", "")),
                str(arguments.get("symbol_b", "")),
                config.quotes_csv,
                use_live=config.use_live_market_data,
            )
        if name == "portfolio_summary":
            return portfolio_summary_live(
                config.holdings_csv,
                config.quotes_csv,
                use_live=config.use_live_market_data,
            )
        if name == "get_stock_history":
            return fetch_stock_history(
                str(arguments.get("symbol", "")).strip(),
                _int(arguments, "days", 30) or 30,
            )
        if name == "get_fx_usdcny":
            return fetch_fx_usdcny()
        return {"error": f"未知工具: {name}"}

    return dispatch

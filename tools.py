"""工具 schema + 本地实现 + 统一 dispatch（基于 tool_registry）。"""
from __future__ import annotations

from datetime import datetime
from typing import Any, Callable

from config import AppConfig
from finance_tools import (
    bond_yield_estimate,
    cagr,
    compound_interest,
    inflation_adjust,
    loan_monthly_payment,
    max_drawdown,
    pct_change,
    rule_of_72,
    savings_goal_monthly,
    sharpe_ratio,
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
from tool_metadata import enrich_tool_result
from tool_registry import register_tool, tool_definitions, get_handler


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


def _num_list(args: dict[str, Any], key: str) -> list[float]:
    raw = args.get(key, [])
    if not isinstance(raw, list):
        return []
    out: list[float] = []
    for v in raw:
        try:
            out.append(float(v))
        except (TypeError, ValueError):
            continue
    return out


@register_tool(
    "get_current_time",
    "返回当前本地日期与时间（本机时区）。",
    {},
)
def _tool_get_current_time() -> dict[str, Any]:
    return {
        "iso": datetime.now().isoformat(timespec="seconds"),
        "note": "时间为运行本脚本的机器本地时间。",
    }


@register_tool(
    "calculate",
    "计算仅含数字与 + - * / ( ) 和空格的数学表达式。",
    {
        "expression": {"type": "string", "description": "数学表达式"},
    },
    required=["expression"],
)
def _tool_calculate(expression: str = "") -> dict[str, Any]:
    allowed = set("0123456789+-*/().")
    if not expression or not all(c in allowed or c.isspace() for c in expression):
        return {"error": "表达式仅允许数字与 + - * / ( ) 及空格。"}
    try:
        value = eval(expression, {"__builtins__": {}}, {})
    except Exception as e:
        return {"error": f"计算失败: {e}"}
    return {"expression": expression.strip(), "result": value}


@register_tool(
    "search_knowledge",
    "从本地知识库检索金融概念、产品说明、工具使用说明等文本片段。",
    {
        "query": {"type": "string", "description": "检索关键词或问句"},
    },
    required=["query"],
)
def _tool_search_knowledge_placeholder() -> dict[str, Any]:
    return {"error": "search_knowledge 需通过 make_dispatch 调用"}


@register_tool(
    "compound_interest",
    "复利终值计算。annual_rate_pct 为年化百分比，如 3 表示 3%。",
    {
        "principal": {"type": "number", "description": "本金"},
        "annual_rate_pct": {"type": "number", "description": "年化利率(%)"},
        "years": {"type": "number", "description": "年数"},
        "compounds_per_year": {"type": "integer", "description": "每年复利次数，默认 12"},
    },
    required=["principal", "annual_rate_pct", "years"],
)
def _tool_compound_interest(
    principal: float = 0,
    annual_rate_pct: float = 0,
    years: float = 0,
    compounds_per_year: int = 12,
) -> dict[str, Any]:
    return enrich_tool_result(
        compound_interest(principal, annual_rate_pct, years, compounds_per_year or 12),
        category="finance",
    )


@register_tool(
    "simple_interest",
    "单利终值计算。",
    {
        "principal": {"type": "number"},
        "annual_rate_pct": {"type": "number"},
        "years": {"type": "number"},
    },
    required=["principal", "annual_rate_pct", "years"],
)
def _tool_simple_interest(principal: float = 0, annual_rate_pct: float = 0, years: float = 0) -> dict[str, Any]:
    return enrich_tool_result(simple_interest(principal, annual_rate_pct, years), category="finance")


@register_tool(
    "loan_monthly_payment",
    "等额本息房贷/贷款月供估算。",
    {
        "principal": {"type": "number", "description": "贷款本金"},
        "annual_rate_pct": {"type": "number", "description": "年化利率(%)"},
        "months": {"type": "integer", "description": "还款月数"},
    },
    required=["principal", "annual_rate_pct", "months"],
)
def _tool_loan_monthly_payment(
    principal: float = 0, annual_rate_pct: float = 0, months: int = 0
) -> dict[str, Any]:
    return enrich_tool_result(loan_monthly_payment(principal, annual_rate_pct, months), category="finance")


@register_tool(
    "savings_goal_monthly",
    "为达到目标金额，估算每月定投金额（复利近似）。",
    {
        "target_amount": {"type": "number"},
        "annual_rate_pct": {"type": "number"},
        "months": {"type": "integer"},
    },
    required=["target_amount", "annual_rate_pct", "months"],
)
def _tool_savings_goal_monthly(
    target_amount: float = 0, annual_rate_pct: float = 0, months: int = 0
) -> dict[str, Any]:
    return enrich_tool_result(
        savings_goal_monthly(target_amount, annual_rate_pct, months), category="finance"
    )


@register_tool(
    "pct_change",
    "计算两数值之间的涨跌额与涨跌幅(%)",
    {
        "old_value": {"type": "number"},
        "new_value": {"type": "number"},
    },
    required=["old_value", "new_value"],
)
def _tool_pct_change(old_value: float = 0, new_value: float = 0) -> dict[str, Any]:
    return enrich_tool_result(pct_change(old_value, new_value), category="finance")


@register_tool(
    "cagr",
    "复合年增长率 CAGR (%)",
    {
        "begin_value": {"type": "number"},
        "end_value": {"type": "number"},
        "years": {"type": "number"},
    },
    required=["begin_value", "end_value", "years"],
)
def _tool_cagr(begin_value: float = 0, end_value: float = 0, years: float = 0) -> dict[str, Any]:
    return enrich_tool_result(cagr(begin_value, end_value, years), category="finance")


@register_tool(
    "rule_of_72",
    "72 法则：估算本金翻倍所需年数",
    {
        "annual_rate_pct": {"type": "number", "description": "年化收益率(%)"},
    },
    required=["annual_rate_pct"],
)
def _tool_rule_of_72(annual_rate_pct: float = 0) -> dict[str, Any]:
    return enrich_tool_result(rule_of_72(annual_rate_pct), category="finance")


@register_tool(
    "inflation_adjust",
    "按通胀率折现名义金额的购买力（粗算）",
    {
        "nominal_amount": {"type": "number"},
        "annual_inflation_pct": {"type": "number"},
        "years": {"type": "number"},
    },
    required=["nominal_amount", "annual_inflation_pct", "years"],
)
def _tool_inflation_adjust(
    nominal_amount: float = 0, annual_inflation_pct: float = 0, years: float = 0
) -> dict[str, Any]:
    return enrich_tool_result(
        inflation_adjust(nominal_amount, annual_inflation_pct, years), category="finance"
    )


@register_tool(
    "lookup_quote",
    (
        "查询股票/指数收盘价，优先联网：A 股东方财富失败后接 akshare，美股 Stooq/yfinance。"
        "查最新价不要传 date。symbol 如 600519、000636、AAPL；指数如 sh000001。"
    ),
    {
        "symbol": {"type": "string"},
        "date": {
            "type": "string",
            "description": "可选 YYYY-MM-DD。查最新价时不要传；禁止填多年前日期",
        },
    },
    required=["symbol"],
)
def _tool_lookup_quote_placeholder() -> dict[str, Any]:
    return {"error": "lookup_quote 需通过 make_dispatch 调用"}


@register_tool(
    "compare_symbols",
    "对比两只标的最近收盘价与价格比",
    {
        "symbol_a": {"type": "string"},
        "symbol_b": {"type": "string"},
    },
    required=["symbol_a", "symbol_b"],
)
def _tool_compare_symbols_placeholder() -> dict[str, Any]:
    return {"error": "compare_symbols 需通过 make_dispatch 调用"}


@register_tool(
    "portfolio_summary",
    "根据示例持仓文件与联网行情，汇总组合市值与盈亏",
    {},
)
def _tool_portfolio_summary_placeholder() -> dict[str, Any]:
    return {"error": "portfolio_summary 需通过 make_dispatch 调用"}


@register_tool(
    "get_stock_history",
    "获取近 N 日收盘价历史（联网，A 股 akshare / 美股 yfinance）",
    {
        "symbol": {"type": "string"},
        "days": {"type": "integer", "description": "天数，5-120，默认 30"},
    },
    required=["symbol"],
)
def _tool_get_stock_history(symbol: str = "", days: int = 30) -> dict[str, Any]:
    result = fetch_stock_history(symbol.strip(), days or 30)
    return enrich_tool_result(result, category="market", source=result.get("source"))


@register_tool(
    "get_fx_usdcny",
    "查询美元兑人民币汇率（akshare 中行汇价，仅供参考）",
    {},
)
def _tool_get_fx_usdcny() -> dict[str, Any]:
    result = fetch_fx_usdcny()
    return enrich_tool_result(result, category="market", source=result.get("source"))


@register_tool(
    "sharpe_ratio",
    "夏普比率：给定每期收益率序列与无风险利率，计算风险调整后收益。",
    {
        "returns": {
            "type": "array",
            "items": {"type": "number"},
            "description": "每期收益率序列，如 [0.01, -0.02, 0.015]",
        },
        "risk_free_rate": {"type": "number", "description": "每期无风险利率，默认 0"},
    },
    required=["returns"],
)
def _tool_sharpe_ratio(returns: list[float] | None = None, risk_free_rate: float = 0) -> dict[str, Any]:
    return enrich_tool_result(
        sharpe_ratio(returns or [], risk_free_rate), category="finance"
    )


@register_tool(
    "max_drawdown",
    "最大回撤：给定价格序列计算从峰值到谷底的最大跌幅(%)。",
    {
        "prices": {
            "type": "array",
            "items": {"type": "number"},
            "description": "价格序列，如 [100, 105, 98, 110]",
        },
    },
    required=["prices"],
)
def _tool_max_drawdown(prices: list[float] | None = None) -> dict[str, Any]:
    return enrich_tool_result(max_drawdown(prices or []), category="finance")


@register_tool(
    "bond_yield_estimate",
    "债券到期收益率 YTM 近似（年付息）。",
    {
        "face": {"type": "number", "description": "面值"},
        "price": {"type": "number", "description": "当前价格"},
        "years": {"type": "number", "description": "剩余年限"},
        "coupon_rate": {"type": "number", "description": "票面利率(%)"},
    },
    required=["face", "price", "years", "coupon_rate"],
)
def _tool_bond_yield_estimate(
    face: float = 0, price: float = 0, years: float = 0, coupon_rate: float = 0
) -> dict[str, Any]:
    return enrich_tool_result(
        bond_yield_estimate(face, price, years, coupon_rate), category="finance"
    )


def make_dispatch(config: AppConfig, index: KnowledgeIndex) -> Callable[[str, dict[str, Any]], dict[str, Any]]:
    def dispatch(name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        if name == "search_knowledge":
            q = str(arguments.get("query", "")).strip()
            if not q:
                return {"error": "query 不能为空"}
            return index.search(q, config.rag_top_k)
        if name == "lookup_quote":
            sym = str(arguments.get("symbol", "")).strip()
            raw_date = str(arguments.get("date", "")).strip() or None
            result = lookup_quote_with_fallback(
                sym,
                config.quotes_csv,
                raw_date,
                use_live=config.use_live_market_data,
                ttl_seconds=config.quote_cache_ttl_seconds,
                cache_dir=config.quote_cache_dir,
            )
            return enrich_tool_result(
                result,
                category="market",
                source=result.get("source"),
                data_as_of=result.get("trade_date") or result.get("date"),
            )
        if name == "compare_symbols":
            result = compare_symbols_live(
                str(arguments.get("symbol_a", "")),
                str(arguments.get("symbol_b", "")),
                config.quotes_csv,
                use_live=config.use_live_market_data,
                ttl_seconds=config.quote_cache_ttl_seconds,
                cache_dir=config.quote_cache_dir,
            )
            return enrich_tool_result(result, category="market")
        if name == "portfolio_summary":
            result = portfolio_summary_live(
                config.holdings_csv,
                config.quotes_csv,
                use_live=config.use_live_market_data,
                ttl_seconds=config.quote_cache_ttl_seconds,
                cache_dir=config.quote_cache_dir,
            )
            return enrich_tool_result(result, category="market", source=result.get("source"))

        handler = get_handler(name)
        if handler is None:
            return {"error": f"未知工具: {name}"}

        if name in ("get_stock_history", "get_fx_usdcny", "sharpe_ratio", "max_drawdown", "bond_yield_estimate"):
            if name == "get_stock_history":
                return handler(
                    str(arguments.get("symbol", "")).strip(),
                    _int(arguments, "days", 30) or 30,
                )
            if name == "sharpe_ratio":
                return handler(_num_list(arguments, "returns"), _num(arguments, "risk_free_rate"))
            if name == "max_drawdown":
                return handler(_num_list(arguments, "prices"))
            if name == "bond_yield_estimate":
                return handler(
                    _num(arguments, "face"),
                    _num(arguments, "price"),
                    _num(arguments, "years"),
                    _num(arguments, "coupon_rate"),
                )
            return handler()

        if name == "calculate":
            return handler(str(arguments.get("expression", "")))
        if name == "compound_interest":
            return handler(
                _num(arguments, "principal"),
                _num(arguments, "annual_rate_pct"),
                _num(arguments, "years"),
                _int(arguments, "compounds_per_year", 12) or 12,
            )
        if name == "simple_interest":
            return handler(
                _num(arguments, "principal"),
                _num(arguments, "annual_rate_pct"),
                _num(arguments, "years"),
            )
        if name == "loan_monthly_payment":
            return handler(
                _num(arguments, "principal"),
                _num(arguments, "annual_rate_pct"),
                _int(arguments, "months"),
            )
        if name == "savings_goal_monthly":
            return handler(
                _num(arguments, "target_amount"),
                _num(arguments, "annual_rate_pct"),
                _int(arguments, "months"),
            )
        if name == "pct_change":
            return handler(_num(arguments, "old_value"), _num(arguments, "new_value"))
        if name == "cagr":
            return handler(
                _num(arguments, "begin_value"),
                _num(arguments, "end_value"),
                _num(arguments, "years"),
            )
        if name == "rule_of_72":
            return handler(_num(arguments, "annual_rate_pct"))
        if name == "inflation_adjust":
            return handler(
                _num(arguments, "nominal_amount"),
                _num(arguments, "annual_inflation_pct"),
                _num(arguments, "years"),
            )

        return handler()

    return dispatch

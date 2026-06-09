"""CLI 与 Web 共用的 Agent 会话逻辑。"""
from __future__ import annotations

from typing import Any, Callable

from config import AppConfig
from orchestrator import run_turn
from rag import KnowledgeIndex
from tools import make_dispatch
from trace import TraceSession
from zai import ZhipuAiClient

SYSTEM_PROMPT = (
    "你是金融学习场景下的智能助手，语气专业、简洁。"
    "涉及复利、单利、房贷月供、定投、CAGR、72 法则、通胀折现、涨跌幅等数值问题时，"
    "必须调用对应金融工具，不要心算。"
    "查询股价、指数、历史走势、汇率、标的对比或组合盈亏时，"
    "调用 lookup_quote、get_stock_history、get_fx_usdcny、compare_symbols 或 portfolio_summary。"
    "查最新收盘价时 lookup_quote 不要传 date；禁止传多年前日期。"
    "行情优先联网（A 股：东方财富后接 akshare），失败再用本地 CSV。"
    "需要准确时间或简单四则运算时，可调用 get_current_time 或 calculate。"
    "回答知识库中的概念、产品说明、风险提示前，先调用 search_knowledge，不要编造。"
    "用户同时问行情和理财计算时，可依次调用多个工具再综合回答。"
    "回复中注明数据来源；行情仅供参考，不构成投资建议。"
)


def validate_api_key(config: AppConfig) -> None:
    if not config.zhipu_api_key:
        raise SystemExit("请配置 ZHIPU_API_KEY（.env 或环境变量）。")
    if not config.zhipu_api_key.isascii():
        raise SystemExit(
            "ZHIPU_API_KEY 须为纯 ASCII。检查 .env 是否保存、是否误用中文占位符。"
        )


def create_session(config: AppConfig, trace: TraceSession | None = None) -> dict[str, Any]:
    validate_api_key(config)
    trace = trace or TraceSession.new(config.trace_jsonl_dir)
    client = ZhipuAiClient(api_key=config.zhipu_api_key)
    index = KnowledgeIndex(config.knowledge_dir, config.rag_chunk_size, config.rag_chunk_overlap)
    dispatch = make_dispatch(config, index)
    messages: list[dict[str, Any]] = [{"role": "system", "content": SYSTEM_PROMPT}]
    trace.emit("session_start", model=config.glm_model)
    return {
        "config": config,
        "client": client,
        "trace": trace,
        "dispatch": dispatch,
        "messages": messages,
    }


def chat(
    session: dict[str, Any],
    user_text: str,
    *,
    on_tool_event: Callable[[str, str, str], None] | None = None,
) -> str:
    messages = session["messages"]
    trace: TraceSession = session["trace"]
    messages.append({"role": "user", "content": user_text})
    trace.stats["user_turns"] += 1
    trace.emit("user_message", preview=user_text[:200])
    return run_turn(
        session["client"],
        session["config"],
        messages,
        session["dispatch"],
        trace,
        on_tool_event=on_tool_event,
    )

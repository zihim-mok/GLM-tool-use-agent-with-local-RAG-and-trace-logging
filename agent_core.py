"""CLI 与 Web 共用的 Agent 会话逻辑。"""
from __future__ import annotations

from typing import Any, Callable

from config import AppConfig
from orchestrator import run_turn
from rag import KnowledgeIndex
from tools import make_dispatch
from trace import TraceSession
from zai import ZhipuAiClient

_BASE_RULES = (
    "涉及复利、单利、房贷月供、定投、CAGR、72 法则、通胀折现、涨跌幅、夏普比率、"
    "最大回撤、债券 YTM 等数值问题时，必须调用对应金融工具，不要心算。"
    "查询股价、指数、历史走势、汇率、标的对比或组合盈亏时，"
    "调用 lookup_quote、get_stock_history、get_fx_usdcny、compare_symbols 或 portfolio_summary。"
    "查最新收盘价时 lookup_quote 不要传 date；禁止传多年前日期。"
    "A 股收盘后当日收盘价仍可通过 lookup_quote 获取；不要用 get_current_time 推断「暂无行情」而拒绝回答。"
    "问 A 股/大盘概况时用 lookup_quote 查 sh000001、sz399001 等指数，不要只调用 get_current_time。"
    "用户纠正、澄清、抱怨或追问（未换新代码/标的）时，优先根据对话中已有 tool 结果作答，"
    "不要重复调用 lookup_quote；应解释 trade_date（交易日期）并说明与查询时刻 retrieved_at 的区别。"
    "行情优先联网（A 股：东方财富后接 akshare），失败再用本地 CSV。"
    "需要准确时间或简单四则运算时，可调用 get_current_time 或 calculate；"
    "同一问题已查过时间则勿重复调用 get_current_time。"
    "回答知识库中的概念、产品说明、风险提示前，先调用 search_knowledge，不要编造。"
    "回复中注明数据来源与 trade_date；行情仅供参考，不构成投资建议。"
)

_SCENE_PROMPTS: dict[str, str] = {
    "educational": (
        "你是金融学习场景下的智能助手，语气专业、耐心，适当解释公式与概念。"
        + _BASE_RULES
        + "用户同时问行情和理财计算时，可依次调用多个工具再综合回答，并简要说明计算逻辑。"
    ),
    "quick": (
        "你是金融快答助手，语气简洁，直接给出关键数字与结论，少废话。"
        + _BASE_RULES
        + "优先一次调用完成所需工具，回答控制在短段落内。"
    ),
    "portfolio": (
        "你是组合分析助手，侧重持仓、盈亏、风险指标与标的对比。"
        + _BASE_RULES
        + "涉及组合时优先 portfolio_summary；需要风险指标时用 sharpe_ratio、max_drawdown。"
        + "对比标的时用 compare_symbols；结合行情与持仓给出结构化小结。"
    ),
}


def get_system_prompt(scene_mode: str) -> str:
    mode = scene_mode.strip().lower()
    return _SCENE_PROMPTS.get(mode, _SCENE_PROMPTS["educational"])


def validate_api_key(config: AppConfig) -> None:
    if not config.zhipu_api_key:
        raise SystemExit("请配置 ZHIPU_API_KEY（.env 或环境变量）。")
    if not config.zhipu_api_key.isascii():
        raise SystemExit(
            "ZHIPU_API_KEY 须为纯 ASCII。检查 .env 是否保存、是否误用中文占位符。"
        )


def create_session(
    config: AppConfig,
    trace: TraceSession | None = None,
    *,
    scene_mode: str | None = None,
) -> dict[str, Any]:
    validate_api_key(config)
    trace = trace or TraceSession.new(config.trace_jsonl_dir)
    client = ZhipuAiClient(api_key=config.zhipu_api_key)
    index = KnowledgeIndex(config.knowledge_dir, config.rag_chunk_size, config.rag_chunk_overlap)
    dispatch = make_dispatch(config, index)
    mode = scene_mode or config.scene_mode
    messages: list[dict[str, Any]] = [{"role": "system", "content": get_system_prompt(mode)}]
    trace.emit("session_start", model=config.glm_model, scene_mode=mode)
    return {
        "config": config,
        "client": client,
        "trace": trace,
        "dispatch": dispatch,
        "messages": messages,
        "scene_mode": mode,
        "tool_dedupe_cache": {},
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
        dedupe_cache=session.setdefault("tool_dedupe_cache", {}),
    )

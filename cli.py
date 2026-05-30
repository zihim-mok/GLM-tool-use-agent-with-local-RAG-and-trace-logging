"""交互入口：配置校验、会话 trace、多轮对话。"""
from __future__ import annotations

from zai import ZhipuAiClient

from config import AppConfig
from orchestrator import run_turn
from rag import KnowledgeIndex
from trace import TraceSession, setup_logging
from tools import make_dispatch


def _end_session(trace: TraceSession, reason: str) -> None:
    trace.emit("session_end", reason=reason, **trace.stats)
    print(
        f"\n[会话统计] 用户轮次={trace.stats['user_turns']} "
        f"LLM 轮次={trace.stats['llm_rounds']} "
        f"工具调用={trace.stats['tool_calls']} "
        f"工具耗时={trace.stats['tool_ms_total']}ms"
    )


def run_interactive() -> None:
    setup_logging()
    config = AppConfig.from_env()

    if not config.zhipu_api_key:
        raise SystemExit("请配置 ZHIPU_API_KEY（.env 或环境变量）。")
    if not config.zhipu_api_key.isascii():
        raise SystemExit(
            "ZHIPU_API_KEY 须为纯 ASCII。检查 .env 是否保存、是否误用中文占位符。"
        )

    trace = TraceSession.new(config.trace_jsonl_dir)
    client = ZhipuAiClient(api_key=config.zhipu_api_key)
    index = KnowledgeIndex(config.knowledge_dir, config.rag_chunk_size, config.rag_chunk_overlap)
    dispatch = make_dispatch(config, index)

    messages: list[dict] = [
        {
            "role": "system",
            "content": (
                "你是助手。需要准确时间或算术时调用对应工具；"
                "涉及本 demo 项目说明、知识库中的固定事实时，先调用 search_knowledge 再回答，不要编造。"
            ),
        },
    ]

    print("模型:", config.glm_model)
    print("知识库目录:", config.knowledge_dir)
    print("trace_id:", trace.trace_id)
    if trace.jsonl_file:
        print("JSONL 日志:", trace.jsonl_file)
    print("输入问题；空行或 quit / exit / q 结束。\n")

    trace.emit("session_start", model=config.glm_model)

    while True:
        try:
            user_text = input("用户: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\n再见。")
            _end_session(trace, "interrupt")
            break
        if not user_text or user_text.lower() in ("quit", "exit", "q"):
            print("再见。")
            _end_session(trace, "quit")
            break

        messages.append({"role": "user", "content": user_text})
        trace.stats["user_turns"] += 1
        trace.emit("user_message", preview=user_text[:200])
        print("---")
        answer = run_turn(client, config, messages, dispatch, trace)
        print("助手:", answer)
        print("---")

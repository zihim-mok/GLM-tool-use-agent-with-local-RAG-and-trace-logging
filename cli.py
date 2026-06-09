"""命令行交互入口。"""
from __future__ import annotations

from agent_core import chat, create_session
from config import AppConfig
from trace import TraceSession, setup_logging


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
    session = create_session(config)

    trace: TraceSession = session["trace"]
    print("模型:", config.glm_model)
    print("知识库:", config.knowledge_dir)
    print("联网行情:", "开启" if config.use_live_market_data else "关闭（仅本地 CSV）")
    print("行情回退:", config.quotes_csv)
    print("trace_id:", trace.trace_id)
    if trace.jsonl_file:
        print("JSONL 日志:", trace.jsonl_file)
    print("输入问题；空行或 quit / exit / q 结束。\n")

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

        print("---")
        answer = chat(session, user_text)
        print("助手:", answer)
        print("---")

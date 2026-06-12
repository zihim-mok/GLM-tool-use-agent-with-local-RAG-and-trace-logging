"""单轮对话内的模型—工具循环 + 观测埋点。"""
from __future__ import annotations

import json
import time
from collections.abc import Callable
from typing import Any

ToolEventCallback = Callable[[str, str, str], None]

from zai import ZhipuAiClient

from config import AppConfig
from memory import trim_messages
from trace import TraceSession
from tool_registry import tool_definitions

_SESSION_DEDUPE_TOOLS = frozenset({"lookup_quote", "compare_symbols"})


def tool_call_cache_key(name: str, args: dict[str, Any]) -> str:
    return json.dumps({"name": name, "args": args}, sort_keys=True, ensure_ascii=False)


def resolve_tool_result(
    name: str,
    args: dict[str, Any],
    dispatch_tool: Callable[[str, dict[str, Any]], dict[str, Any]],
    *,
    turn_cache: dict[str, dict[str, Any]],
    dedupe_cache: dict[str, dict[str, Any]] | None = None,
) -> dict[str, Any]:
    key = tool_call_cache_key(name, args)
    if key in turn_cache:
        out = dict(turn_cache[key])
        out["deduped"] = True
        out["dedupe_scope"] = "turn"
        return out
    if name in _SESSION_DEDUPE_TOOLS and dedupe_cache is not None and key in dedupe_cache:
        out = dict(dedupe_cache[key])
        out["deduped"] = True
        out["dedupe_scope"] = "session"
        return out
    result = dispatch_tool(name, args)
    turn_cache[key] = result
    if (
        name in _SESSION_DEDUPE_TOOLS
        and dedupe_cache is not None
        and "error" not in result
    ):
        dedupe_cache[key] = result
    return result


def run_turn(
    client: ZhipuAiClient,
    config: AppConfig,
    messages: list[dict[str, Any]],
    dispatch_tool: Callable[[str, dict[str, Any]], dict[str, Any]],
    trace: TraceSession,
    on_tool_event: ToolEventCallback | None = None,
    dedupe_cache: dict[str, dict[str, Any]] | None = None,
) -> str:
    tools = tool_definitions()
    turn_cache: dict[str, dict[str, Any]] = {}
    for round_i in range(config.max_tool_rounds):
        trace.stats["llm_rounds"] += 1
        trace.emit("llm_request", round=round_i, message_count=len(messages))
        response = client.chat.completions.create(
            model=config.glm_model,
            messages=messages,
            tools=tools,
            tool_choice="auto",
        )
        message = response.choices[0].message
        usage = getattr(response, "usage", None)
        usage_dict = usage.model_dump() if usage is not None and hasattr(usage, "model_dump") else None
        trace.emit(
            "llm_response",
            round=round_i,
            has_tool_calls=bool(message.tool_calls),
            usage=usage_dict,
        )

        messages.append(message.model_dump())

        if not message.tool_calls:
            text = message.content or ""
            trace.emit("assistant_final", round=round_i, preview=text[:200] if text else "")
            trim_messages(messages, config.max_context_messages)
            return text

        for tc in message.tool_calls:
            fn = tc.function
            raw_args = fn.arguments or "{}"
            try:
                args = json.loads(raw_args)
            except json.JSONDecodeError:
                args = {}
            trace.emit("tool_call", name=fn.name, arguments_preview=raw_args[:500])
            t0 = time.perf_counter()
            result = resolve_tool_result(
                fn.name,
                args,
                dispatch_tool,
                turn_cache=turn_cache,
                dedupe_cache=dedupe_cache,
            )
            duration_ms = int((time.perf_counter() - t0) * 1000)
            trace.stats["tool_calls"] += 1
            trace.stats["tool_ms_total"] += duration_ms
            payload = json.dumps(result, ensure_ascii=False)
            trace.emit(
                "tool_result",
                name=fn.name,
                duration_ms=duration_ms,
                result_preview=payload[:500],
            )
            messages.append(
                {
                    "role": "tool",
                    "tool_call_id": tc.id,
                    "content": payload,
                }
            )
            if on_tool_event is not None:
                on_tool_event(fn.name, raw_args, payload)
            else:
                print(f"  [tool] {fn.name}({raw_args}) -> {payload[:300]}{'...' if len(payload) > 300 else ''}")

    trace.emit("abort_max_tool_rounds", limit=config.max_tool_rounds)
    trim_messages(messages, config.max_context_messages)
    return f"[中止] 已达到最大工具轮次上限 {config.max_tool_rounds}。"

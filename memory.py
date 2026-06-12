"""对话记忆：按用户轮次截断，保留完整 tool 调用链。"""
from __future__ import annotations

from typing import Any


def _is_tool_chain_start(msg: dict[str, Any]) -> bool:
    """assistant 带 tool_calls 的消息是 tool 链起点。"""
    if msg.get("role") != "assistant":
        return False
    tool_calls = msg.get("tool_calls")
    return bool(tool_calls)


def _tool_chain_length(messages: list[dict[str, Any]], start: int) -> int:
    """从 assistant(tool_calls) 起，包含后续连续 tool 消息的长度。"""
    if start >= len(messages) or not _is_tool_chain_start(messages[start]):
        return 1
    length = 1
    i = start + 1
    while i < len(messages) and messages[i].get("role") == "tool":
        length += 1
        i += 1
    return length


def _count_user_turns(messages: list[dict[str, Any]], start_idx: int = 0) -> int:
    return sum(1 for m in messages[start_idx:] if m.get("role") == "user")


def trim_messages(
    messages: list[dict[str, Any]],
    max_messages: int,
    *,
    max_user_turns: int | None = None,
) -> None:
    """原地截断：保留 system + 尾部消息，不拆开 tool 调用链。

    max_messages：总条数上限（含 system）。
    max_user_turns：若指定，按用户轮次裁剪（仍遵守 max_messages 与 tool 链完整）。
    """
    if not messages:
        return

    has_system = messages[0].get("role") == "system"
    start_idx = 1 if has_system else 0

    if max_user_turns is not None and max_user_turns > 0:
        while _count_user_turns(messages, start_idx) > max_user_turns:
            _drop_oldest_block(messages, start_idx)
            if len(messages) <= max_messages:
                return

    while len(messages) > max_messages:
        if len(messages) <= start_idx + 1:
            break
        _drop_oldest_block(messages, start_idx)


def _drop_oldest_block(messages: list[dict[str, Any]], start_idx: int) -> None:
    """删除最旧可移除块：优先独立 user/assistant，最后才删完整 tool 链。"""
    if len(messages) <= start_idx:
        return
    for i in range(start_idx, len(messages)):
        role = messages[i].get("role")
        if role == "user":
            del messages[i]
            return
        if role == "assistant" and not _is_tool_chain_start(messages[i]):
            del messages[i]
            return
    idx = start_idx
    if _is_tool_chain_start(messages[idx]):
        chain_len = _tool_chain_length(messages, idx)
        del messages[idx:idx + chain_len]
    else:
        del messages[idx]

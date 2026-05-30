"""对话记忆：截断上下文，避免 messages 无限增长。"""
from __future__ import annotations

from typing import Any


def trim_messages(messages: list[dict[str, Any]], max_messages: int) -> None:
    """原地保留 system（若有）+ 尾部若干条，使总长度不超过 max_messages。

    策略：从索引 1 起删除最旧消息，直到 len <= max_messages。
    教学用简单策略；生产环境可按「用户轮次」或「不拆 tool 序列」再细化。
    """
    if len(messages) <= max_messages:
        return
    has_system = bool(messages and messages[0].get("role") == "system")
    drop_until = len(messages) - max_messages
    if has_system:
        # 始终保留 messages[0]
        for _ in range(drop_until):
            if len(messages) <= max_messages:
                break
            if len(messages) > 1:
                del messages[1]
    else:
        del messages[:drop_until]

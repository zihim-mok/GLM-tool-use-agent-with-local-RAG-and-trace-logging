"""工具 schema + 本地实现 + 统一 dispatch。"""
from __future__ import annotations

import json
from datetime import datetime
from typing import Any, Callable

from config import AppConfig
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
                        "expression": {
                            "type": "string",
                            "description": "数学表达式字符串",
                        }
                    },
                    "required": ["expression"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "search_knowledge",
                "description": (
                    "从本地知识库检索与问题相关的文本片段。回答关于 demo_agent、"
                    "项目说明、固定事实等问题前应先调用此工具，再结合检索结果作答。"
                ),
                "parameters": {
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": "检索查询，用简短关键词或完整问句均可",
                        }
                    },
                    "required": ["query"],
                },
            },
        },
    ]


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
        return {"error": f"未知工具: {name}"}

    return dispatch

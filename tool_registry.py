"""工具注册中心：schema 定义 + handler 统一注册。"""
from __future__ import annotations

from typing import Any, Callable

ToolHandler = Callable[..., dict[str, Any]]

_REGISTRY: dict[str, dict[str, Any]] = {}


def register_tool(
    name: str,
    description: str,
    parameters: dict[str, Any],
    *,
    required: list[str] | None = None,
) -> Callable[[ToolHandler], ToolHandler]:
    """注册工具 schema 与 handler。"""

    def decorator(fn: ToolHandler) -> ToolHandler:
        props = parameters.get("properties", parameters)
        req = required or parameters.get("required", [])
        _REGISTRY[name] = {
            "handler": fn,
            "schema": {
                "type": "function",
                "function": {
                    "name": name,
                    "description": description,
                    "parameters": {
                        "type": "object",
                        "properties": props,
                        "required": req,
                    },
                },
            },
        }
        return fn

    return decorator


def tool_definitions() -> list[dict[str, Any]]:
    return [entry["schema"] for entry in _REGISTRY.values()]


def get_handler(name: str) -> ToolHandler | None:
    entry = _REGISTRY.get(name)
    return entry["handler"] if entry else None


def registered_tool_names() -> list[str]:
    return list(_REGISTRY.keys())

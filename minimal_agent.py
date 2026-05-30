"""
demo_agent 入口：先加载 .env，再启动 CLI。

模块划分：env_loader / config / trace / memory / rag / tools / orchestrator / cli
"""
from __future__ import annotations

from env_loader import load_env_file

load_env_file()

from cli import run_interactive

if __name__ == "__main__":
    run_interactive()

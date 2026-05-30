# demo_agent：智谱 GLM + 工具调用 + 可观测链路 + 轻量 RAG

## 亮点（简历可写）

- **模块化 Agent 编排**：`orchestrator` 实现 GLM 工具调用闭环，工具层 / RAG / 记忆 / 观测解耦。
- **全链路可观测**：`trace_id` + JSONL 记录 LLM 请求、工具耗时、会话统计；`analyze_trace.py` 可复盘单次对话。
- **零向量依赖 RAG**：本地 md/txt 滑动切块 + TF-IDF 检索，降低学习与部署成本。
- **工程防护**：工具轮次上限、上下文截断、表达式白名单计算。

## 准备

1. Python 3.10+ 推荐。
2. 安装 **`zai-sdk`**（勿装 PyPI 占位包 **`zai`**）。

```bash
cd demo_agent
python -m venv .venv
.\.venv\Scripts\activate
pip install -r requirements.txt
```

3. 复制 `.env.example` 为 `.env`，填入 `ZHIPU_API_KEY`。`.env` 会覆盖同名系统环境变量。

## 运行

```bash
python minimal_agent.py
```

Windows 若无法 `activate` 虚拟环境，可直接双击 **`run.bat`**，或：

```powershell
.\.venv\Scripts\python.exe minimal_agent.py
```

多轮对话；空行或 `quit` / `exit` / `q` 退出。启动时会打印 **trace_id** 与 JSONL 路径（若开启）。

**仓库**：https://github.com/zihim-mok/GLM-tool-use-agent-with-local-RAG-and-trace-logging

## 目录与模块（学习用分层）

| 文件 | 作用 |
|------|------|
| `minimal_agent.py` | 入口：加载 `.env` 后启动 CLI |
| `cli.py` | 交互循环、创建 `TraceSession`、组装 client / 知识库 / dispatch |
| `orchestrator.py` | 单轮内「请求 GLM → 执行 tool → 再请求」循环 + trace 埋点 |
| `tools.py` | `tool_definitions()` + `make_dispatch()`（时间、计算器、**search_knowledge**） |
| `rag.py` | 读取 `knowledge/*.md|txt`，切块，**TF-IDF** 词面检索 |
| `memory.py` | 每轮结束后按 `MAX_CONTEXT_MESSAGES` **截断** `messages` |
| `trace.py` | `trace_id` + 控制台日志 + `logs/<uuid>.jsonl`；会话级统计 |
| `analyze_trace.py` | 解析 JSONL，输出事件时间线与工具耗时汇总 |
| `config.py` | `AppConfig.from_env()` 集中读环境变量 |
| `env_loader.py` | 解析 `.env` |
| `knowledge/` | 示例 `demo_notes.md`，可自行增删 |

## 环境变量（可选）

见 `.env.example`：`MAX_TOOL_ROUNDS`、`MAX_CONTEXT_MESSAGES`、`KNOWLEDGE_DIR`、`RAG_*`、`TRACE_JSONL_DIR`（设为 `0` / `false` / `off` 可关闭写 JSONL）。

## 复盘 trace

```bash
python analyze_trace.py logs/<trace_id>.jsonl
```

## 试试 RAG

在 `knowledge/` 里编辑或新增 `.md`，然后提问例如：「demo 的示例代号是什么？」「orchestrator 是干什么的？」模型应倾向先调用 `search_knowledge`。

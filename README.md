# FinAgent：可观测的智谱 GLM 金融 Tool-Use Agent

面向金融场景的 Tool-Use Agent：14 个确定性工具（复利/房贷/行情/组合）+ 本地 TF-IDF RAG + JSONL 全链路 Trace + Gradio Web。

**仓库**：https://github.com/zihim-mok/GLM-tool-use-agent-with-local-RAG-and-trace-logging  
**项目说明（简历/答辩用）**：见 [PROJECT.md](./PROJECT.md)

## 亮点

- **Tool-Use 多轮编排**：`orchestrator` 实现 GLM 工具调用闭环，CLI/Web 共用 `agent_core`
- **全链路可观测**：`trace_id` + JSONL 记录 LLM 请求、工具耗时；`analyze_trace.py` 可复盘
- **多级行情兜底**：东财 → akshare → 腾讯证券 → 本地 CSV；工具层拦截离谱 `date`
- **零向量 RAG**：本地 md/txt + TF-IDF，无 embedding API 依赖
- **工程防护**：工具轮次上限、上下文截断、表达式白名单计算

## 准备

1. Python 3.10+
2. 安装依赖（勿装 PyPI 占位包 `zai`，应装 `zai-sdk`）

```bash
cd demo_agent
python -m venv .venv
.\.venv\Scripts\activate
pip install -r requirements.txt
```

3. 复制 `.env.example` 为 `.env`，填入智谱 `ZHIPU_API_KEY`

## 运行

### 命令行

```bash
python minimal_agent.py
```

或双击 **`run.bat`** /：

```powershell
.\.venv\Scripts\python.exe minimal_agent.py
```

### Web 页面（Gradio）

```bash
python web_app.py
```

或双击 **`run_web.bat`**，浏览器打开 `http://127.0.0.1:7860`

## 内置工具

| 类别 | 工具 |
|------|------|
| 通用 | `get_current_time`, `calculate`, `search_knowledge` |
| 理财计算 | `compound_interest`, `simple_interest`, `loan_monthly_payment`, `savings_goal_monthly` |
| 指标 | `pct_change`, `cagr`, `rule_of_72`, `inflation_adjust` |
| 行情/组合 | `lookup_quote`, `get_stock_history`, `get_fx_usdcny`, `compare_symbols`, `portfolio_summary` |

**联网行情**（默认开启，失败自动回退本地 CSV）：

| 数据 | 优先数据源 | 备用 |
|------|-----------|------|
| A 股 | 东方财富 push2 API | akshare → 腾讯证券 → CSV |
| A 股指数 | 东方财富 | — |
| 美股 | 东方财富 / Stooq | yfinance |
| 美元兑人民币 | 东方财富 / frankfurter.app | — |
| 历史 K 线 | akshare（A 股）/ Stooq（美股） | — |

关闭联网：`.env` 设 `USE_LIVE_MARKET_DATA=false`

## 试试这些问题

- `600519 最近收盘价多少`
- `1 万本金年化 3% 按月复利存 5 年多少钱`
- `贷款 80 万、年利率 4.5%、30 年每月还多少`
- `帮我看看示例组合盈亏`
- `年化 8% 几年翻倍`
- `AAPL 和 MSFT 股价对比`
- `复利和单利有什么区别`

## 目录

| 文件 | 作用 |
|------|------|
| `minimal_agent.py` | CLI 入口 |
| `web_app.py` | Gradio Web 入口 |
| `agent_core.py` | CLI/Web 共用会话与系统提示 |
| `orchestrator.py` | 模型与工具多轮循环 |
| `tools.py` / `finance_tools.py` | 工具定义与实现 |
| `rag.py` | 本地 md/txt + TF-IDF 检索 |
| `trace.py` / `analyze_trace.py` | JSONL 日志与复盘 |
| `knowledge/` | 金融 FAQ 等文档 |
| `data/` | 示例行情与持仓 CSV |
| `PROJECT.md` | 项目背景、架构、简历话术、面试备答 |

## 环境变量

见 `.env.example`：`GLM_MODEL`、`QUOTES_CSV`、`HOLDINGS_CSV`、`WEB_PORT` 等。

## 复盘 trace

```bash
python analyze_trace.py logs/<trace_id>.jsonl
```

## 试试 RAG

在 `knowledge/` 里编辑或新增 `.md`，然后提问例如：复利和单利有什么区别？ or demo 的示例代号是什么？ 模型应倾向先调用 `search_knowledge`。

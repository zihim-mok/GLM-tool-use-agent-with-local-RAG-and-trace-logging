# FinAgent：可观测的智谱 GLM 金融 Tool-Use Agent

**副标题**：本地 RAG · 多级行情兜底 · JSONL 链路追踪 · Gradio 演示

**项目类型**：个人技术学习项目（AI/DS 方向 · 金融科技场景）  
**完成时间**：2026 年 5 月  
**完成形式**：独立完成  
**开源地址**：https://github.com/zihim-mok/GLM-tool-use-agent-with-local-RAG-and-trace-logging

---

## 一、项目背景

1. 大模型在金融问答中普遍存在**数值幻觉**（复利、房贷、CAGR 等心算错误）、**行情编造**、**概念缺乏依据**三类问题，难以直接用于学习与演示场景。
2. 通用 ChatBot 缺少**工具调用编排**、**数据来源标注**和**调用链路复盘**能力，调试成本高，不利于 Agent 学习与面试展示。
3. 免费行情 API（如东方财富）不稳定，模型还可能传入**离谱日期参数**（如把「昨天」错填成 2021 年），导致查询失败或答非所问。
4. 本项目聚焦**可落地的 Agent 工程范式**，独立设计并开发了一套**智谱 GLM Tool-Use 金融助手 Demo**：用确定性金融工具替代心算，用本地 RAG 约束概念回答，用多级行情兜底保证可用性，用 JSONL Trace 记录完整「用户 → LLM → 工具 → 回复」链路，支持 CLI 与 Gradio Web 双入口演示。

---

## 二、核心 Demo 功能与技术实现

### 整体技术架构

采用**四层 Agent 流水线**，模块解耦、CLI/Web 共用核心逻辑：

1. **会话与编排层**：`agent_core.py` + `orchestrator.py`，多轮 Tool-Use 循环
2. **工具与计算层**：`tools.py` + `finance_tools.py`，14 个结构化金融工具
3. **数据与知识层**：`market_data.py` 联网行情 + `rag.py` 本地 TF-IDF 检索
4. **可观测与交互层**：`trace.py` JSONL 日志 + `web_app.py` Gradio 6 界面

### 核心功能模块

#### 1. 多工具金融 Agent 编排模块

- 基于 **zai-sdk** 对接智谱 GLM（默认 `glm-4-flash`），实现 `tools` + `tool_choice=auto`
- 设计 **14 个工具**：通用 3 个 + 理财计算 8 个 + 行情/组合 3 个
- `SYSTEM_PROMPT` 强制规则：数值必调工具、概念先 RAG、行情注明来源、不构成投资建议
- `memory.py` 上下文裁剪，控制多轮对话 token 成本

#### 2. 确定性金融计算工具集

- 复利/单利、等额本息月供、定投月投入、涨跌幅、CAGR、72 法则、通胀折现
- 本地 CSV 行情查询、双标的比价、示例组合盈亏汇总
- 所有工具返回 **结构化 JSON**，便于模型引用与 Trace 复盘

#### 3. 多级兜底联网行情模块（`market_data.py`）

- **A 股实时**：东方财富 push2 → akshare（东财历史）→ **腾讯证券**（东财挂掉时的真正备用）
- **美股**：东方财富 / Stooq → yfinance
- **汇率**：东方财富 USD/CNY → frankfurter.app
- **离线兜底**：`data/quotes.csv`（含 600519、000636、000823 等常用票）
- **`sanitize_quote_date()`**：拒绝未来日期、格式错误、超过 400 天的离谱历史日期
- 返回字段含 `source`、`fallback`、`note`，满足可解释与可审计

#### 4. 轻量本地 RAG 模块（`rag.py`）

- 无需 Embedding API：本地 `md/txt` 切块 + **TF-IDF 词面检索**
- 支持中英文与 CJK 粗粒度分词，零额外向量依赖
- 知识库：`knowledge/finance_faq.md` 等金融 FAQ

#### 5. 全链路可观测模块（`trace.py` + `analyze_trace.py`）

- 每会话生成唯一 `trace_id`，落盘 `logs/<uuid>.jsonl`
- 记录：`session_start`、`llm_request/response`、`tool_call`、`tool_result`（含耗时）、`assistant_final`
- 统计 LLM 轮次、工具调用次数、工具总耗时，支持命令行复盘演示

#### 6. Gradio Web 交互界面（`web_app.py`）

- 适配 **Gradio 6**（role/content 消息格式）
- FinAgent 深色金融风 UI：对话区 + 实时工具调用面板
- 与 CLI 共用 `create_session` / `chat`，行为一致

### Demo 完整运行流程

1. **启动**：`run.bat`（CLI）或 `run_web.bat`（Web `127.0.0.1:7860`）
2. **用户提问**：如「000636 最近收盘价」「80 万房贷 30 年月供多少」
3. **模型决策**：选择 `lookup_quote` / `loan_monthly_payment` 等工具
4. **工具执行**：行情走多级兜底，计算走确定性公式
5. **多轮补充**：缺信息时自动追加工具调用
6. **Trace 记录**：全程 JSONL 落盘
7. **自然语言回复**：附数据来源与风险提示

---

## 三、技术栈

| 类别 | 技术 |
|------|------|
| 编程语言 | Python 3.10+ |
| 大模型 | 智谱 GLM（zai-sdk）、Tool-Use 多轮编排 |
| Agent 工程 | 工具 Schema、会话管理、上下文裁剪 |
| 行情数据 | requests、akshare、yfinance、Stooq、frankfurter |
| 数据处理 | Pandas |
| 检索 | 自研 TF-IDF RAG（无 embedding） |
| 前端 | Gradio 6 |
| 可观测 | JSONL Trace + 分析脚本 |

---

## 四、个人核心贡献

1. **独立完成 Agent 全流程工程**：从 Prompt 设计、工具 Schema、编排循环到双端入口。
2. **设计多级行情兜底架构**：识别 akshare 历史接口仍走东财的局限，引入腾讯证券备用链，联网失败自动回退 CSV。
3. **实现工具层参数防护**：`date` 校验拦截模型乱填年份，降低 Tool-Use 失败率。
4. **构建轻量可观测体系**：JSONL 全链路日志 + 复盘脚本，便于调试与面试演示。
5. **零向量依赖本地 RAG**：TF-IDF 检索金融 FAQ，成本低、可离线、易理解。
6. **开源可复现**：完整 `requirements.txt`、`run.bat`、README。

---

## 五、核心运行结果

1. **功能验证**
   - 理财计算类问题均通过工具返回，避免心算幻觉
   - A 股在东财 `RemoteDisconnected` 时，可通过腾讯证券源返回实时价
   - 模型误传 `date=2021-08-06` 时，工具层直接拒绝并提示「查最新价勿传 date」
   - 联网全挂时，`000636`/`000823` 可回退 `quotes.csv`，带 `fallback: true`

2. **对比传统方案**
   - vs 纯 ChatBot：有工具约束，数值与行情更可靠
   - vs 单源行情脚本：多级 fallback，演示稳定性更高
   - vs 向量 RAG：TF-IDF 更轻、更适合学习向 Demo

---

## 六、分岗位适配描述

### AI 应用 / Agent 工程师版

1. 基于智谱 GLM 实现 Tool-Use 多轮编排，设计 14 个金融工具 Schema 与分发逻辑。
2. 构建 Prompt + 工具双层约束，解决大模型金融数值幻觉与行情编造问题。
3. 实现 JSONL 全链路 Trace，支持 Agent 调试、复盘与效果演示。
4. 设计行情多级 Fallback 与工具参数校验，提升真实网络环境下的鲁棒性。

### 后端 / 全栈版

1. 模块化分层架构，CLI/Web 共用核心。
2. 对接多个外部行情 API，封装重试、降级、离线 CSV 兜底。
3. 基于 Gradio 6 开发 Web Demo，自定义 CSS。
4. 环境变量驱动配置（`.env`），支持开关联网行情、Trace 目录、模型名等。

### 金融科技版

1. 覆盖行情查询、组合盈亏、汇率、理财测算等 fintech 常见问答。
2. 强调数据来源标注与「不构成投资建议」合规提示。
3. 本地知识库 + 工具计算，适合金融概念教学与 Agent 范式演示。

---

## 七、英文版精简描述

Independently built **FinAgent**, a Zhipu GLM-powered financial Tool-Use agent with local TF-IDF RAG and full JSONL trace logging.  
Implemented 14 structured finance tools to eliminate LLM numerical hallucination.  
Designed a multi-tier market data pipeline (Eastmoney → akshare → Tencent → local CSV) with date-parameter validation.  
Delivered dual interfaces (CLI + Gradio 6 Web) with step-by-step tool-call visibility.  
Open-sourced on GitHub with reproducible setup.

---

## 八、面试高频问题（备答提纲）

### 技术类

1. **Tool-Use 循环怎么实现的？** — `orchestrator.run_turn` 每轮调 GLM；若有 `tool_calls` 则执行工具、把结果塞回 messages，直到输出纯文本或达轮次上限。
2. **为什么不用 Embedding RAG？** — 学习场景下 TF-IDF 足够；零 API 成本、可离线、逻辑透明。
3. **行情多级兜底怎么设计的？** — 东财 push2 → akshare 东财历史 → 腾讯证券 → CSV。
4. **怎么防止模型传错 date？** — 工具层 `sanitize_quote_date` + Prompt 约束。
5. **Trace 日志有什么用？** — 复盘模型选了什么工具、参数对不对、耗时多少。

### 业务类

1. **和真实投顾系统差在哪？** — 学习 Demo，无实盘；但工具化 + 来源标注是正确方向。
2. **为什么金融场景必须 Tool-Use？** — 金额、利率要求可核验，纯生成式风险高。

### 复盘类

1. **最大挑战？** — 东财 API 不稳定 + 模型乱填日期；通过腾讯备用源 + 参数校验 + CSV 兜底解决。
2. **重做会改什么？** — 工具注册中心、行情缓存、向量 RAG、单元测试覆盖。

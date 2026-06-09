# demo_agent 项目说明（知识库示例）

- **项目代号**：DEMO-AGENT-01
- **定位**：教学向可观测 LLM Agent，基于智谱 GLM 工具调用。
- **核心模块**：`orchestrator` 负责「模型请求 → 工具执行 → 再请求」循环；`trace` 记录全链路 JSONL；`rag` 从本目录检索片段。
- **RAG 策略**：本地 md/txt 滑动窗口切块 + TF-IDF 词面检索，无需 embedding 服务。
- **内置工具**：通用 3 个 + 金融工具 11 个（复利、房贷、行情、组合等），详见 `finance_faq.md`。

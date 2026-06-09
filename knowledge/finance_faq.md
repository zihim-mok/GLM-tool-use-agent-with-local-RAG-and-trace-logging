# 金融助手知识库

## 产品定位

本助手用于**金融概念学习与 Agent 演示**，支持复利/单利、房贷月供、定投测算、行情与持仓查询。**行情优先联网**：A 股与指数来自 akshare（东方财富），美股来自 yfinance（Yahoo Finance），失败时回退本地 CSV。**不构成投资建议。**

## 工具一览

| 场景 | 工具 |
|------|------|
| 复利终值 | compound_interest |
| 单利终值 | simple_interest |
| 房贷月供 | loan_monthly_payment |
| 涨跌幅 | pct_change |
| 复合年增长率 CAGR | cagr |
| 72 法则翻倍年数 | rule_of_72 |
| 通胀折现购买力 | inflation_adjust |
| 每月定投达成目标 | savings_goal_monthly |
| 查收盘价/指数 | lookup_quote（600519、AAPL、sh000001） |
| 近 N 日历史 | get_stock_history |
| 美元兑人民币 | get_fx_usdcny |
| 两标的比价 | compare_symbols |
| 示例组合盈亏 | portfolio_summary |

## 概念速查

- **复利**：利息并入本金再计息；默认可按月复利（每年 12 次）。
- **单利**：仅对本金计息，I = P × r × t。
- **等额本息**：月供固定；前期利息占比高。
- **CAGR**：跨期年化收益率，适合比较不同投资区间。
- **72 法则**：翻倍年数约等于 72 除以年化收益率（%）。

## 示例数据

- 行情：`data/quotes.csv`（含 600519、000001、601318、AAPL、MSFT）
- 持仓：`data/holdings.csv`（演示组合盈亏）

## 风险提示

计算与行情均为教学示例；实盘决策请使用权威数据源并独立判断。

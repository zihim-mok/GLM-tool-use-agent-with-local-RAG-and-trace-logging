"""金融领域本地工具（示例数据，非实时行情，不构成投资建议）。"""
from __future__ import annotations

import csv
import math
from pathlib import Path
from typing import Any


def compound_interest(
    principal: float,
    annual_rate_pct: float,
    years: float,
    compounds_per_year: int = 12,
) -> dict[str, Any]:
    if principal <= 0:
        return {"error": "本金须大于 0"}
    if years <= 0:
        return {"error": "年限须大于 0"}
    if compounds_per_year <= 0:
        return {"error": "复利次数须大于 0"}

    r = annual_rate_pct / 100.0
    n = compounds_per_year
    amount = principal * (1 + r / n) ** (n * years)
    return {
        "principal": round(principal, 2),
        "annual_rate_pct": annual_rate_pct,
        "years": years,
        "compounds_per_year": n,
        "future_value": round(amount, 2),
        "interest_earned": round(amount - principal, 2),
        "formula": "FV = P * (1 + r/n)^(n*t)",
    }


def simple_interest(
    principal: float,
    annual_rate_pct: float,
    years: float,
) -> dict[str, Any]:
    if principal <= 0 or years <= 0:
        return {"error": "本金与年限须大于 0"}
    r = annual_rate_pct / 100.0
    interest = principal * r * years
    return {
        "principal": round(principal, 2),
        "annual_rate_pct": annual_rate_pct,
        "years": years,
        "interest_earned": round(interest, 2),
        "future_value": round(principal + interest, 2),
        "formula": "I = P * r * t",
    }


def loan_monthly_payment(
    principal: float,
    annual_rate_pct: float,
    months: int,
) -> dict[str, Any]:
    if principal <= 0 or months <= 0:
        return {"error": "本金与期数须大于 0"}
    if annual_rate_pct < 0:
        return {"error": "年利率不能为负"}

    if annual_rate_pct == 0:
        payment = principal / months
    else:
        rm = annual_rate_pct / 100.0 / 12.0
        payment = principal * rm * (1 + rm) ** months / ((1 + rm) ** months - 1)

    total_paid = payment * months
    return {
        "principal": round(principal, 2),
        "annual_rate_pct": annual_rate_pct,
        "months": months,
        "monthly_payment": round(payment, 2),
        "total_paid": round(total_paid, 2),
        "total_interest": round(total_paid - principal, 2),
        "note": "等额本息近似，仅供参考。",
    }


def pct_change(old_value: float, new_value: float) -> dict[str, Any]:
    if old_value == 0:
        return {"error": "原值不能为 0"}
    change = new_value - old_value
    return {
        "old_value": old_value,
        "new_value": new_value,
        "change": round(change, 4),
        "change_pct": round(change / old_value * 100, 4),
    }


def cagr(begin_value: float, end_value: float, years: float) -> dict[str, Any]:
    if begin_value <= 0 or end_value <= 0 or years <= 0:
        return {"error": "期初值、期末值、年数均须大于 0"}
    rate = (end_value / begin_value) ** (1 / years) - 1
    return {
        "begin_value": round(begin_value, 2),
        "end_value": round(end_value, 2),
        "years": years,
        "cagr_pct": round(rate * 100, 4),
        "formula": "CAGR = (End/Begin)^(1/t) - 1",
    }


def rule_of_72(annual_rate_pct: float) -> dict[str, Any]:
    if annual_rate_pct <= 0:
        return {"error": "年化收益率须大于 0"}
    years_to_double = 72 / annual_rate_pct
    return {
        "annual_rate_pct": annual_rate_pct,
        "years_to_double_approx": round(years_to_double, 2),
        "note": "72 法则为心算近似：翻倍年数 ≈ 72 / 年化收益率(%)",
    }


def inflation_adjust(
    nominal_amount: float,
    annual_inflation_pct: float,
    years: float,
) -> dict[str, Any]:
    if nominal_amount <= 0 or years < 0:
        return {"error": "金额须大于 0，年数不能为负"}
    factor = (1 + annual_inflation_pct / 100.0) ** years
    real_value = nominal_amount / factor
    return {
        "nominal_amount": round(nominal_amount, 2),
        "annual_inflation_pct": annual_inflation_pct,
        "years": years,
        "purchasing_power_today": round(real_value, 2),
        "note": "按复利通胀折现购买力，粗算参考。",
    }


def _load_quotes(csv_path: Path) -> list[dict[str, str]]:
    if not csv_path.is_file():
        return []
    with csv_path.open(encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def lookup_quote(
    symbol: str,
    csv_path: Path,
    date: str | None = None,
) -> dict[str, Any]:
    sym = symbol.strip().upper()
    if not sym:
        return {"error": "股票代码不能为空"}

    rows = [r for r in _load_quotes(csv_path) if r.get("symbol", "").strip().upper() == sym]
    if not rows:
        return {"error": f"未找到 {sym}，请查看 data/quotes.csv"}

    if date:
        matched = [r for r in rows if r.get("date", "").strip() == date.strip()]
        if not matched:
            dates = sorted({r.get("date", "") for r in rows})[-5:]
            return {"error": f"{sym} 在 {date} 无记录", "recent_dates": dates}
        row = matched[0]
    else:
        rows.sort(key=lambda r: r.get("date", ""))
        row = rows[-1]

    close = float(row["close"])
    prev = [r for r in rows if r.get("date", "") < row.get("date", "")]
    change_pct = None
    if prev:
        prev_close = float(prev[-1]["close"])
        if prev_close:
            change_pct = round((close - prev_close) / prev_close * 100, 2)

    return {
        "symbol": sym,
        "name": row.get("name", ""),
        "date": row.get("date", ""),
        "close": close,
        "volume": int(float(row.get("volume", 0) or 0)),
        "change_pct_vs_prev": change_pct,
        "source": "本地示例 CSV，非实时行情",
    }


def compare_symbols(
    symbol_a: str,
    symbol_b: str,
    csv_path: Path,
) -> dict[str, Any]:
    qa = lookup_quote(symbol_a, csv_path)
    qb = lookup_quote(symbol_b, csv_path)
    if "error" in qa:
        return qa
    if "error" in qb:
        return qb
    return {
        "symbol_a": qa,
        "symbol_b": qb,
        "price_ratio_a_over_b": round(qa["close"] / qb["close"], 4) if qb["close"] else None,
        "note": "基于各自最近可用收盘价对比。",
    }


def portfolio_summary(holdings_path: Path, quotes_path: Path) -> dict[str, Any]:
    if not holdings_path.is_file():
        return {"error": f"持仓文件不存在: {holdings_path}"}

    quotes_rows = _load_quotes(quotes_path)
    latest: dict[str, dict[str, str]] = {}
    for r in quotes_rows:
        sym = r.get("symbol", "").strip().upper()
        if not sym:
            continue
        if sym not in latest or r.get("date", "") > latest[sym].get("date", ""):
            latest[sym] = r

    positions: list[dict[str, Any]] = []
    total_cost = 0.0
    total_market = 0.0

    with holdings_path.open(encoding="utf-8", newline="") as f:
        for row in csv.DictReader(f):
            sym = row.get("symbol", "").strip().upper()
            shares = float(row.get("shares", 0) or 0)
            cost = float(row.get("avg_cost", 0) or 0)
            if not sym or shares <= 0:
                continue
            q = latest.get(sym)
            if not q:
                positions.append({"symbol": sym, "error": "无行情"})
                continue
            price = float(q["close"])
            market = shares * price
            cost_basis = shares * cost
            pnl = market - cost_basis
            pnl_pct = (pnl / cost_basis * 100) if cost_basis else None
            total_cost += cost_basis
            total_market += market
            positions.append(
                {
                    "symbol": sym,
                    "name": q.get("name", ""),
                    "shares": shares,
                    "avg_cost": cost,
                    "last_close": price,
                    "market_value": round(market, 2),
                    "cost_basis": round(cost_basis, 2),
                    "pnl": round(pnl, 2),
                    "pnl_pct": round(pnl_pct, 2) if pnl_pct is not None else None,
                }
            )

    total_pnl = total_market - total_cost
    return {
        "positions": positions,
        "total_cost_basis": round(total_cost, 2),
        "total_market_value": round(total_market, 2),
        "total_pnl": round(total_pnl, 2),
        "total_pnl_pct": round(total_pnl / total_cost * 100, 2) if total_cost else None,
        "source": "本地示例持仓与行情，非实盘",
    }


def sharpe_ratio(
    returns: list[float],
    risk_free_rate: float = 0.0,
) -> dict[str, Any]:
    """夏普比率：超额收益均值 / 收益标准差（按每期收益，非年化调整）。"""
    if not returns or len(returns) < 2:
        return {"error": "returns 至少需要 2 个数值"}
    n = len(returns)
    excess = [r - risk_free_rate for r in returns]
    mean_ex = sum(excess) / n
    var = sum((x - mean_ex) ** 2 for x in excess) / (n - 1)
    std = math.sqrt(var)
    if std == 0:
        return {"error": "收益标准差为 0，无法计算夏普比率"}
    sharpe = mean_ex / std
    return {
        "periods": n,
        "risk_free_rate": risk_free_rate,
        "mean_excess_return": round(mean_ex, 6),
        "std_excess_return": round(std, 6),
        "sharpe_ratio": round(sharpe, 4),
        "note": "未年化调整的夏普比率，仅供学习参考。",
    }


def max_drawdown(prices: list[float]) -> dict[str, Any]:
    """最大回撤：从峰值到谷底的最大跌幅 (%)。"""
    if not prices or len(prices) < 2:
        return {"error": "prices 至少需要 2 个数值"}
    peak = prices[0]
    max_dd = 0.0
    peak_idx = 0
    trough_idx = 0
    best_peak_idx = 0
    for i, p in enumerate(prices):
        if p > peak:
            peak = p
            peak_idx = i
        if peak > 0:
            dd = (peak - p) / peak
            if dd > max_dd:
                max_dd = dd
                trough_idx = i
                best_peak_idx = peak_idx
    return {
        "periods": len(prices),
        "max_drawdown_pct": round(max_dd * 100, 4),
        "peak_index": best_peak_idx,
        "trough_index": trough_idx,
        "peak_price": round(prices[best_peak_idx], 4),
        "trough_price": round(prices[trough_idx], 4),
        "formula": "max((peak - price) / peak)",
    }


def bond_yield_estimate(
    face: float,
    price: float,
    years: float,
    coupon_rate: float,
) -> dict[str, Any]:
    """债券到期收益率 YTM 近似（平价付息，牛顿迭代）。"""
    if face <= 0 or price <= 0 or years <= 0:
        return {"error": "面值、价格、年限均须大于 0"}
    if coupon_rate < 0:
        return {"error": "票面利率不能为负"}
    coupon = face * coupon_rate / 100.0
    ytm = coupon_rate / 100.0
    for _ in range(50):
        if abs(1 + ytm) < 1e-9:
            break
        pv_coupons = sum(coupon / (1 + ytm) ** t for t in range(1, int(years) + 1))
        pv_face = face / (1 + ytm) ** years
        f = pv_coupons + pv_face - price
        df = 0.0
        for t in range(1, int(years) + 1):
            df -= t * coupon / (1 + ytm) ** (t + 1)
        df -= years * face / (1 + ytm) ** (years + 1)
        if abs(df) < 1e-12:
            break
        ytm -= f / df
    return {
        "face": round(face, 2),
        "price": round(price, 2),
        "years": years,
        "coupon_rate_pct": coupon_rate,
        "annual_coupon": round(coupon, 2),
        "ytm_pct": round(ytm * 100, 4),
        "note": "年付息 YTM 近似，仅供学习演示。",
    }


def savings_goal_monthly(
    target_amount: float,
    annual_rate_pct: float,
    months: int,
) -> dict[str, Any]:
    """已知目标金额与年化收益，估算每月定投（期末一次性投入近似）。"""
    if target_amount <= 0 or months <= 0:
        return {"error": "目标金额与月数须大于 0"}
    if annual_rate_pct < 0:
        return {"error": "年利率不能为负"}

    if annual_rate_pct == 0:
        monthly = target_amount / months
    else:
        rm = annual_rate_pct / 100.0 / 12.0
        # FV = PMT * ((1+r)^n - 1) / r  => PMT = FV * r / ((1+r)^n - 1)
        monthly = target_amount * rm / ((1 + rm) ** months - 1)

    return {
        "target_amount": round(target_amount, 2),
        "annual_rate_pct": annual_rate_pct,
        "months": months,
        "monthly_contribution": round(monthly, 2),
        "note": "按每月月末定投、复利计息近似，仅供参考。",
    }

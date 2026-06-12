"""联网行情：A 股/指数直连东方财富，美股 Stooq/yfinance，失败回退 akshare 与本地 CSV。"""
from __future__ import annotations

import re
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Callable

import pandas as pd
import requests

_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
)
_SESSION = requests.Session()
_SESSION.headers.update({"User-Agent": _USER_AGENT, "Referer": "https://finance.eastmoney.com/"})

_INDEX_MAP = {
    "sh000001": "1.000001",
    "sz399001": "0.399001",
    "sz399006": "0.399006",
    "000001": "1.000001",
    "399001": "0.399001",
}


# 指定日期若早于该天数，视为模型乱填（如 2021），改查最近交易日
_MAX_QUOTE_DATE_AGE_DAYS = 400


def sanitize_quote_date(date: str | None) -> tuple[str | None, dict[str, Any] | None]:
    """校验行情 date；过旧/未来/格式错误时返回 error dict。"""
    if date is None or not str(date).strip():
        return None, None
    raw = str(date).strip()[:10]
    try:
        d = datetime.strptime(raw, "%Y-%m-%d").date()
    except ValueError:
        return None, {"error": f"日期格式无效: {date}，请使用 YYYY-MM-DD 或不要传 date"}
    today = datetime.now().date()
    if d > today:
        return None, {"error": f"日期 {raw} 在未来，无法查询"}
    age = (today - d).days
    if age > _MAX_QUOTE_DATE_AGE_DAYS:
        return None, {
            "error": (
                f"日期 {raw} 过旧（距今天 {age} 天）。"
                "查询最新收盘价请不要传 date；若确需历史价格请核对日期。"
            ),
            "hint": "omit_date_for_latest",
        }
    return raw, None


def enrich_quote_date_fields(result: dict[str, Any]) -> dict[str, Any]:
    """为行情结果标注 trade_date，便于区分交易日与查询时刻。"""
    if "error" in result:
        return result
    out = dict(result)
    trade = str(out.get("trade_date") or out.get("date") or "").strip()
    if trade:
        out["trade_date"] = trade
        out.setdefault("date", trade)
    market = str(out.get("market") or "")
    if market in ("A股", "A股指数"):
        out["price_label"] = "收盘价"
        out["trade_date_note"] = (
            "trade_date 为本条行情所属的 A 股交易日；"
            "收盘后仍可通过 lookup_quote 获取当日收盘价。"
            "retrieved_at 为本次查询时刻。"
        )
    return out


def _retry(fn: Callable[[], dict[str, Any]], attempts: int = 3) -> dict[str, Any]:
    last_err: Exception | None = None
    for i in range(attempts):
        try:
            return fn()
        except Exception as e:
            last_err = e
            if i < attempts - 1:
                time.sleep(0.8 * (i + 1))
    return {"error": f"请求失败: {last_err}"}


def _is_a_share(symbol: str) -> bool:
    return bool(re.fullmatch(r"\d{6}", symbol.strip()))


def _is_index(symbol: str) -> bool:
    s = symbol.strip().lower()
    return s.startswith(("sh", "sz")) or s in _INDEX_MAP


def _a_share_secid(code: str) -> str:
    return f"1.{code}" if code.startswith("6") else f"0.{code}"


def _normalize_index(symbol: str) -> str:
    s = symbol.strip().lower()
    if s in _INDEX_MAP:
        return _INDEX_MAP[s]
    if s.startswith(("sh", "sz")) and s[2:] in _INDEX_MAP:
        return _INDEX_MAP[s[2:]]
    return _INDEX_MAP.get(s, s)


def _fetch_eastmoney_secid(secid: str, market_label: str) -> dict[str, Any]:
    url = "https://push2.eastmoney.com/api/qt/stock/get"
    resp = _SESSION.get(
        url,
        params={"secid": secid, "fields": "f57,f58,f43,f44,f45,f46,f47,f48,f60,f170,f86"},
        timeout=12,
    )
    resp.raise_for_status()
    data = resp.json().get("data") or {}
    if not data:
        return {"error": f"东方财富无数据 secid={secid}"}

    price = (data.get("f43") or 0) / 100.0
    prev = (data.get("f60") or 0) / 100.0
    change_pct = data.get("f170")
    if change_pct is not None:
        change_pct = round(float(change_pct) / 100.0, 2)

    ts = data.get("f86")
    date_str = ""
    if ts:
        try:
            date_str = datetime.fromtimestamp(int(ts)).strftime("%Y-%m-%d")
        except (TypeError, ValueError, OSError):
            date_str = str(ts)

    return {
        "symbol": str(data.get("f57") or secid.split(".")[-1]),
        "name": str(data.get("f58") or ""),
        "date": date_str or datetime.now().strftime("%Y-%m-%d"),
        "open": round((data.get("f46") or 0) / 100.0, 4),
        "high": round((data.get("f44") or 0) / 100.0, 4),
        "low": round((data.get("f45") or 0) / 100.0, 4),
        "close": round(price, 4),
        "prev_close": round(prev, 4) if prev else None,
        "volume": int(data.get("f47") or 0),
        "change_pct_vs_prev": change_pct,
        "source": "东方财富 push2 API",
        "market": market_label,
    }


def _normalize_ohlcv_df(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df.columns = [str(c).strip().lower() for c in df.columns]
    required = {"date", "open", "high", "low", "close", "volume"}
    if not required.issubset(df.columns):
        return pd.DataFrame()
    return df.dropna(subset=["close"])


def _fetch_stooq_us(symbol: str) -> dict[str, Any]:
    sym = symbol.strip().lower().removesuffix(".us")
    url = f"https://stooq.com/q/d/l/?s={sym}.us&i=d"
    df = _normalize_ohlcv_df(pd.read_csv(url))
    if df.empty:
        return {"error": f"Stooq 无 {symbol} 数据"}
    r = df.iloc[-1]
    prev = df.iloc[-2] if len(df) > 1 else None
    close = float(r["close"])
    change_pct = None
    if prev is not None:
        pc = float(prev["close"])
        if pc:
            change_pct = round((close - pc) / pc * 100, 2)
    return {
        "symbol": symbol.upper(),
        "name": symbol.upper(),
        "date": str(r["date"]),
        "open": float(r["open"]),
        "high": float(r["high"]),
        "low": float(r["low"]),
        "close": close,
        "volume": int(r["volume"]) if pd.notna(r["volume"]) else 0,
        "change_pct_vs_prev": change_pct,
        "source": "Stooq",
        "market": "美股",
    }


def _fetch_eastmoney_us(symbol: str) -> dict[str, Any]:
    sym = symbol.strip().upper()
    for prefix in ("105", "106"):
        result = _fetch_eastmoney_secid(f"{prefix}.{sym}", "美股")
        if "error" not in result and result.get("close"):
            return result
    return {"error": f"东方财富无美股 {sym} 数据"}


def _fetch_yfinance(symbol: str, date: str | None = None) -> dict[str, Any]:
    import yfinance as yf

    ticker = yf.Ticker(symbol)
    hist = ticker.history(period="1mo" if date else "10d", auto_adjust=True)
    if hist is None or hist.empty:
        return {"error": f"yfinance 无 {symbol} 数据"}
    hist = hist.reset_index()
    if date:
        target = datetime.strptime(date, "%Y-%m-%d").date()
        row = hist[hist["Date"].dt.date == target]
        if row.empty:
            return {"error": f"{symbol} 在 {date} 无数据"}
        r = row.iloc[-1]
        prev = None
    else:
        r = hist.iloc[-1]
        prev = hist.iloc[-2] if len(hist) > 1 else None
    close = float(r["Close"])
    change_pct = None
    if prev is not None and not date:
        pc = float(prev["Close"])
        if pc:
            change_pct = round((close - pc) / pc * 100, 2)
    return {
        "symbol": symbol.upper(),
        "name": symbol.upper(),
        "date": str(r["Date"].date()) if hasattr(r["Date"], "date") else str(r["Date"])[:10],
        "close": close,
        "volume": int(r["Volume"]),
        "change_pct_vs_prev": change_pct,
        "source": "yfinance",
        "market": "美股/全球",
    }


def _tx_symbol(code: str) -> str:
    return f"sh{code}" if code.startswith("6") else f"sz{code}"


def _parse_hist_df(df: pd.DataFrame, code: str, date: str | None, source: str) -> dict[str, Any]:
    if df is None or df.empty:
        return {"error": f"{source} 无 {code} 数据"}

    df = df.copy()
    df["_d"] = pd.to_datetime(df["date"], errors="coerce").dt.strftime("%Y-%m-%d")
    df = df.dropna(subset=["_d", "close"])
    if df.empty:
        return {"error": f"{source} 无 {code} 有效数据"}

    if date:
        row = df[df["_d"] == date]
        if row.empty:
            return {"error": f"{code} 在 {date} 无数据", "recent_dates": df["_d"].tail(5).tolist()}
        r = row.iloc[-1]
        prev_rows = df[df["_d"] < date]
        prev = prev_rows.iloc[-1] if not prev_rows.empty else None
    else:
        r = df.iloc[-1]
        prev = df.iloc[-2] if len(df) > 1 else None

    close = float(r["close"])
    change_pct = None
    if prev is not None:
        pc = float(prev["close"])
        if pc:
            change_pct = round((close - pc) / pc * 100, 2)

    volume = int(r["volume"]) if "volume" in r and pd.notna(r.get("volume")) else None
    out: dict[str, Any] = {
        "symbol": code,
        "name": "",
        "date": str(r["_d"]),
        "close": close,
        "change_pct_vs_prev": change_pct,
        "source": source,
        "market": "A股",
    }
    if volume is not None:
        out["volume"] = volume
    return out


def _fetch_akshare_hist(code: str, date: str | None = None) -> dict[str, Any]:
    import akshare as ak

    if date:
        target = datetime.strptime(date, "%Y-%m-%d").date()
        start = (target - timedelta(days=10)).strftime("%Y%m%d")
        end = (target + timedelta(days=5)).strftime("%Y%m%d")
    else:
        end = datetime.now().strftime("%Y%m%d")
        start = (datetime.now() - timedelta(days=60)).strftime("%Y%m%d")

    df = ak.stock_zh_a_hist(symbol=code, period="daily", start_date=start, end_date=end, adjust="qfq")
    if df is None or df.empty:
        return {"error": f"akshare 无 {code} 数据"}
    norm = df.rename(columns={"日期": "date", "收盘": "close", "成交量": "volume"})
    return _parse_hist_df(norm, code, date, "akshare（东方财富）")


def _fetch_tx_hist(code: str, date: str | None = None) -> dict[str, Any]:
    import akshare as ak

    if date:
        target = datetime.strptime(date, "%Y-%m-%d").date()
        start = (target - timedelta(days=10)).strftime("%Y%m%d")
        end = (target + timedelta(days=5)).strftime("%Y%m%d")
    else:
        end = datetime.now().strftime("%Y%m%d")
        start = (datetime.now() - timedelta(days=60)).strftime("%Y%m%d")

    df = ak.stock_zh_a_hist_tx(symbol=_tx_symbol(code), start_date=start, end_date=end, adjust="qfq")
    if df is None or df.empty:
        return {"error": f"腾讯证券 无 {code} 数据"}
    return _parse_hist_df(df, code, date, "akshare（腾讯证券）")


def _fetch_a_share_hist_chain(sym: str, date: str | None) -> dict[str, Any]:
    """东方财富 akshare 失败后走腾讯证券。"""
    last: dict[str, Any] = {"error": "A 股历史行情不可用"}
    for fetcher, label in ((_fetch_akshare_hist, "akshare"), (_fetch_tx_hist, "腾讯证券")):
        result = _retry(lambda f=fetcher, s=sym, d=date: f(s, d), attempts=2)
        if "error" not in result:
            return result
        last = result
        last["tried"] = label
    return last


def _fetch_a_share_live(sym: str, date: str | None) -> dict[str, Any]:
    """A 股：东方财富实时 -> akshare/腾讯；指定日期失败时回退最近交易日。"""
    if date:
        hist = _fetch_a_share_hist_chain(sym, date)
        if "error" not in hist:
            return hist
        latest = _fetch_a_share_hist_chain(sym, None)
        if "error" not in latest:
            latest["note"] = f"指定日期 {date} 未取到，已返回最近可用交易日"
            latest["requested_date"] = date
            return latest
        em = _retry(lambda: _fetch_eastmoney_secid(_a_share_secid(sym), "A股"), attempts=1)
        if "error" not in em:
            em["note"] = f"指定日期 {date} 未取到，已返回东方财富最近行情"
            return em
        return hist if hist else latest

    em = _retry(lambda: _fetch_eastmoney_secid(_a_share_secid(sym), "A股"), attempts=2)
    if "error" not in em:
        return em
    hist = _fetch_a_share_hist_chain(sym, None)
    if "error" not in hist:
        hist["note"] = "东方财富 push2 不可用，已改用 " + str(hist.get("source", "备用行情"))
        return hist
    return em if em else hist


def fetch_live_quote(symbol: str, date: str | None = None) -> dict[str, Any]:
    sym = symbol.strip()
    if not sym:
        return {"error": "代码不能为空"}

    clean_date, date_err = sanitize_quote_date(date)
    if date_err:
        return date_err
    date = clean_date

    if _is_index(sym):
        secid = _normalize_index(sym)
        em = _retry(lambda: _fetch_eastmoney_secid(secid, "A股指数"), attempts=2)
        return enrich_quote_date_fields(em)

    if _is_a_share(sym):
        return enrich_quote_date_fields(_fetch_a_share_live(sym, date))

    if date:
        return enrich_quote_date_fields(_retry(lambda: _fetch_yfinance(sym.upper(), date)))

    for fetcher in (_fetch_eastmoney_us, _fetch_stooq_us):
        result = _retry(lambda f=fetcher: f(sym), attempts=2)
        if "error" not in result:
            return enrich_quote_date_fields(result)
    return enrich_quote_date_fields(_retry(lambda: _fetch_yfinance(sym.upper()), attempts=2))


def fetch_stock_history(symbol: str, days: int = 30) -> dict[str, Any]:
    days = max(5, min(days, 120))
    sym = symbol.strip()
    if not sym:
        return {"error": "代码不能为空"}

    if _is_a_share(sym):
        import akshare as ak

        end = datetime.now().strftime("%Y%m%d")
        start = (datetime.now() - timedelta(days=days + 15)).strftime("%Y%m%d")

        def _ak():
            df = ak.stock_zh_a_hist(symbol=sym, period="daily", start_date=start, end_date=end, adjust="qfq")
            if df is None or df.empty:
                return {"error": f"无法获取 {sym} 历史"}
            tail = df.tail(days)
            return {
                "symbol": sym,
                "days": len(tail),
                "history": [
                    {"date": str(r["日期"]), "close": float(r["收盘"]), "volume": int(r["成交量"])}
                    for _, r in tail.iterrows()
                ],
                "source": "akshare",
            }

        return _retry(_ak)

    def _us():
        sym_l = sym.lower().removesuffix(".us")
        url = f"https://stooq.com/q/d/l/?s={sym_l}.us&i=d"
        df = _normalize_ohlcv_df(pd.read_csv(url))
        if df.empty:
            return {"error": f"无法获取 {sym} 历史"}
        tail = df.tail(days)
        return {
            "symbol": sym.upper(),
            "days": len(tail),
            "history": [
                {
                    "date": str(r["date"]),
                    "close": float(r["close"]),
                    "volume": int(r["volume"]) if pd.notna(r["volume"]) else 0,
                }
                for _, r in tail.iterrows()
            ],
            "source": "Stooq",
        }

    return _retry(_us)


def fetch_fx_usdcny() -> dict[str, Any]:
    def _em():
        url = "https://push2.eastmoney.com/api/qt/stock/get"
        resp = _SESSION.get(url, params={"secid": "133.USDCNY", "fields": "f43,f57,f58,f86"}, timeout=12)
        resp.raise_for_status()
        data = resp.json().get("data") or {}
        if not data or not data.get("f43"):
            return {"error": "东方财富 USD/CNY 无数据"}
        rate = float(data["f43"]) / 10000.0
        return {
            "pair": "USD/CNY",
            "rate": round(rate, 4),
            "source": "东方财富 USD/CNY",
            "note": "仅供参考，非交易报价",
        }

    def _frankfurter():
        resp = _SESSION.get("https://api.frankfurter.app/latest?from=USD&to=CNY", timeout=12)
        resp.raise_for_status()
        body = resp.json()
        rate = body.get("rates", {}).get("CNY")
        if not rate:
            return {"error": "frankfurter 无 CNY 汇率"}
        return {
            "pair": "USD/CNY",
            "rate": round(float(rate), 4),
            "date": body.get("date"),
            "source": "frankfurter.app",
            "note": "仅供参考",
        }

    for fn in (_em, _frankfurter):
        result = _retry(fn, attempts=2)
        if "error" not in result:
            return result
    return result


def lookup_quote_with_fallback(
    symbol: str,
    csv_path: Path,
    date: str | None = None,
    *,
    use_live: bool = True,
    ttl_seconds: int = 600,
    cache_dir: Path | None = None,
) -> dict[str, Any]:
    clean_date, date_err = sanitize_quote_date(date)
    if date_err:
        return date_err
    date = clean_date

    if ttl_seconds > 0:
        from quote_cache import get_cached, set_cached

        cached = get_cached(symbol, date, ttl_seconds, cache_dir)
        if cached is not None:
            return enrich_quote_date_fields(cached)

    live_err: dict[str, Any] | None = None
    if use_live:
        try:
            result = fetch_live_quote(symbol, date)
            if "error" not in result:
                result = enrich_quote_date_fields(result)
                if ttl_seconds > 0:
                    from quote_cache import set_cached

                    set_cached(symbol, date, result, cache_dir)
                return result
            live_err = result
        except Exception as e:
            live_err = {"error": f"联网行情失败: {e}"}

    from finance_tools import lookup_quote as local_lookup

    local = local_lookup(symbol, csv_path, date)
    if "error" not in local:
        local = enrich_quote_date_fields(local)
        local["fallback"] = True
        err_msg = live_err.get("error") if live_err else "已关闭"
        local["source"] = f"本地 CSV（联网失败: {err_msg}）"
        if ttl_seconds > 0:
            from quote_cache import set_cached

            set_cached(symbol, date, local, cache_dir)
        return local

    # 指定日期本地也没有时，再试本地最近一条
    if date and _is_a_share(symbol.strip()):
        local_latest = local_lookup(symbol, csv_path, None)
        if "error" not in local_latest:
            local_latest = enrich_quote_date_fields(local_latest)
            local_latest["fallback"] = True
            local_latest["note"] = f"联网与指定日期 {date} 均不可用，已返回 CSV 最近记录"
            return local_latest

    return live_err or local


def compare_symbols_live(
    symbol_a: str,
    symbol_b: str,
    csv_path: Path,
    *,
    use_live: bool = True,
    ttl_seconds: int = 600,
    cache_dir: Path | None = None,
) -> dict[str, Any]:
    qa = lookup_quote_with_fallback(
        symbol_a, csv_path, use_live=use_live, ttl_seconds=ttl_seconds, cache_dir=cache_dir
    )
    qb = lookup_quote_with_fallback(
        symbol_b, csv_path, use_live=use_live, ttl_seconds=ttl_seconds, cache_dir=cache_dir
    )
    if "error" in qa:
        return qa
    if "error" in qb:
        return qb
    return {
        "symbol_a": qa,
        "symbol_b": qb,
        "price_ratio_a_over_b": round(qa["close"] / qb["close"], 4) if qb["close"] else None,
        "note": "基于最近可用收盘价；优先联网数据源。",
    }


def portfolio_summary_live(
    holdings_path: Path,
    csv_path: Path,
    *,
    use_live: bool = True,
    ttl_seconds: int = 600,
    cache_dir: Path | None = None,
) -> dict[str, Any]:
    if not holdings_path.is_file():
        return {"error": f"持仓文件不存在: {holdings_path}"}

    import csv

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
            q = lookup_quote_with_fallback(
                sym,
                csv_path,
                use_live=use_live,
                ttl_seconds=ttl_seconds,
                cache_dir=cache_dir,
            )
            if "error" in q:
                positions.append({"symbol": sym, "error": q["error"]})
                continue
            price = float(q["close"])
            cost_basis = shares * cost
            market = shares * price
            pnl = market - cost_basis
            total_cost += cost_basis
            total_market += market
            positions.append(
                {
                    "symbol": sym,
                    "name": q.get("name", ""),
                    "shares": shares,
                    "avg_cost": cost,
                    "last_close": price,
                    "quote_date": q.get("date"),
                    "market_value": round(market, 2),
                    "cost_basis": round(cost_basis, 2),
                    "pnl": round(pnl, 2),
                    "pnl_pct": round(pnl / cost_basis * 100, 2) if cost_basis else None,
                    "source": q.get("source"),
                }
            )

    total_pnl = total_market - total_cost
    return {
        "positions": positions,
        "total_cost_basis": round(total_cost, 2),
        "total_market_value": round(total_market, 2),
        "total_pnl": round(total_pnl, 2),
        "total_pnl_pct": round(total_pnl / total_cost * 100, 2) if total_cost else None,
        "source": "联网行情优先" if use_live else "本地 CSV",
        "note": "示例持仓，不构成投资建议",
    }

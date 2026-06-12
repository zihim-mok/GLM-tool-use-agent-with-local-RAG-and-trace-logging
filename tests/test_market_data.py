"""market_data 日期校验与缓存测试。"""
from datetime import datetime, timedelta
from pathlib import Path

from market_data import enrich_quote_date_fields, lookup_quote_with_fallback, sanitize_quote_date


def test_sanitize_reject_old_2021():
    clean, err = sanitize_quote_date("2021-08-06")
    assert clean is None
    assert err is not None
    assert "过旧" in err["error"] or "hint" in err


def test_sanitize_reject_future():
    future = (datetime.now().date() + timedelta(days=30)).strftime("%Y-%m-%d")
    clean, err = sanitize_quote_date(future)
    assert clean is None
    assert err is not None
    assert "未来" in err["error"]


def test_sanitize_reject_invalid_format():
    clean, err = sanitize_quote_date("08-06-2021")
    assert clean is None
    assert err is not None
    assert "格式" in err["error"]


def test_sanitize_accepts_recent():
    recent = (datetime.now().date() - timedelta(days=30)).strftime("%Y-%m-%d")
    clean, err = sanitize_quote_date(recent)
    assert err is None
    assert clean == recent


def test_lookup_quote_with_fallback_local():
    root = Path(__file__).resolve().parent.parent
    csv_path = root / "data" / "quotes.csv"
    r = lookup_quote_with_fallback("600519", csv_path, use_live=False, ttl_seconds=0)
    assert "error" not in r
    assert r["symbol"] == "600519"
    assert "close" in r


def test_enrich_quote_date_fields_a_share():
    r = enrich_quote_date_fields(
        {
            "symbol": "600519",
            "date": "2026-06-12",
            "close": 1291.91,
            "market": "A股",
        }
    )
    assert r["trade_date"] == "2026-06-12"
    assert r["price_label"] == "收盘价"
    assert "trade_date_note" in r

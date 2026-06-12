"""lookup_quote_with_fallback 离线回退测试。"""
from pathlib import Path

from market_data import lookup_quote_with_fallback


def test_lookup_local_csv_no_live():
    root = Path(__file__).resolve().parent.parent
    csv_path = root / "data" / "quotes.csv"
    r = lookup_quote_with_fallback("AAPL", csv_path, use_live=False, ttl_seconds=0)
    assert "error" not in r
    assert r["close"] > 0


def test_lookup_unknown_symbol():
    root = Path(__file__).resolve().parent.parent
    csv_path = root / "data" / "quotes.csv"
    r = lookup_quote_with_fallback("ZZZZZZ", csv_path, use_live=False, ttl_seconds=0)
    assert "error" in r


def test_lookup_cache_hit():
    root = Path(__file__).resolve().parent.parent
    csv_path = root / "data" / "quotes.csv"
    cache_dir = root / "data" / "cache_test"
    r1 = lookup_quote_with_fallback(
        "600519", csv_path, use_live=False, ttl_seconds=600, cache_dir=cache_dir
    )
    r2 = lookup_quote_with_fallback(
        "600519", csv_path, use_live=False, ttl_seconds=600, cache_dir=cache_dir
    )
    assert "error" not in r1
    assert r2.get("cached") is True

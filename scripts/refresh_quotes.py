"""拉取近 3 日行情写入本地缓存文件（需联网）。"""
from __future__ import annotations

import csv
import sys
from datetime import datetime, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from env_loader import load_env_file

load_env_file()

from config import AppConfig
from market_data import lookup_quote_with_fallback

SYMBOLS = ["600519", "000001", "601318", "000636", "AAPL", "MSFT", "300750"]


def main() -> None:
    config = AppConfig.from_env()
    cache_dir = config.quote_cache_dir or ROOT / "data" / "cache"
    cache_dir.mkdir(parents=True, exist_ok=True)
    out_csv = ROOT / "data" / "quotes_recent.csv"
    rows: list[dict[str, str]] = []

    for sym in SYMBOLS:
        r = lookup_quote_with_fallback(
            sym,
            config.quotes_csv,
            use_live=True,
            ttl_seconds=0,
            cache_dir=cache_dir,
        )
        if "error" in r:
            print(f"跳过 {sym}: {r['error']}")
            continue
        rows.append(
            {
                "symbol": sym,
                "name": str(r.get("name", "")),
                "date": str(r.get("date", "")),
                "close": str(r.get("close", "")),
                "volume": str(r.get("volume", 0)),
            }
        )
        print(f"OK {sym} {r.get('close')} @ {r.get('date')}")

    if rows:
        with out_csv.open("w", encoding="utf-8", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=["symbol", "name", "date", "close", "volume"])
            writer.writeheader()
            writer.writerows(rows)
        print(f"已写入 {out_csv} ({len(rows)} 条)")
    else:
        print("无数据写入")


if __name__ == "__main__":
    main()

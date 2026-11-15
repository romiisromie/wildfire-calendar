"""Extend a country's record from January of the current year to (almost) today with the FIRMS area API.

    python update_current.py Kazakhstan

Needs a free FIRMS MAP_KEY in .streamlit/secrets.toml (FIRMS_MAP_KEY = "...") or the FIRMS_MAP_KEY environment
variable. The key is never printed or written anywhere else.

Yearly archives stop at the end of last year. For the current year we take MODIS (Terra + Aqua still fly):
standard-processing (SP) data where it exists, near-real-time (NRT) after that. The app converts these MODIS days
to VIIRS units with the same validated monthly factor it uses for 2000–2011.
"""
from __future__ import annotations

import io
import os
import re
import sys
import time
import tomllib
from datetime import date, timedelta
from pathlib import Path

import pandas as pd
import requests

import data

API = "https://firms.modaps.eosdis.nasa.gov/api"
HERE = Path(__file__).parent


def key() -> str:
    k = os.environ.get("FIRMS_MAP_KEY", "")
    f = HERE / ".streamlit" / "secrets.toml"
    if not k and f.exists():
        k = tomllib.loads(f.read_text(encoding="utf-8")).get("FIRMS_MAP_KEY", "")
    k = k.strip()
    if not re.fullmatch(r"[A-Za-z0-9]{16,64}", k):
        raise SystemExit("No valid FIRMS_MAP_KEY found in .streamlit/secrets.toml or the environment.")
    return k


def get(url: str, tries: int = 5) -> str:
    for i in range(tries):
        try:
            r = requests.get(url, timeout=180)
            if r.status_code == 200:
                return r.text
        except requests.RequestException:
            pass
        time.sleep(4 * (i + 1))
    raise SystemExit("FIRMS API request failed repeatedly (the key is not shown here).")


def availability(k: str, source: str) -> tuple[date, date] | None:
    t = get(f"{API}/data_availability/csv/{k}/{source}")
    if "Invalid" in t:
        raise SystemExit("FIRMS says the MAP_KEY is invalid.")
    d = pd.read_csv(io.StringIO(t))
    row = d[d.iloc[:, 0] == source]
    if row.empty:
        return None
    return pd.Timestamp(row.iloc[0, 1]).date(), pd.Timestamp(row.iloc[0, 2]).date()


def fetch(k: str, source: str, bbox, start: date, end: date) -> pd.DataFrame:
    w, s, e, n = (round(v, 3) for v in bbox)
    parts, day = [], start
    while day <= end:
        span = min(5, (end - day).days + 1)  # the API allows at most 5 days per request
        t = get(f"{API}/area/csv/{k}/{source}/{w},{s},{e},{n}/{span}/{day:%Y-%m-%d}")
        if t.strip() and not t.startswith("Invalid"):
            parts.append(pd.read_csv(io.StringIO(t)))
        day += timedelta(days=span)
        print(f"\r{source} {day:%Y-%m-%d}", end="", flush=True)
    print()
    return pd.concat(parts, ignore_index=True) if parts else pd.DataFrame()


def main(country: str) -> None:
    k = key()
    meta = data.meta(country)
    year = date.today().year
    start, end = date(year, 1, 1), date.today() - timedelta(days=1)
    frames = []
    sp = availability(k, "MODIS_SP")
    sp_end = min(sp[1], end) if sp else start - timedelta(days=1)
    if sp and sp_end >= start:
        frames.append(fetch(k, "MODIS_SP", meta["bbox"], start, sp_end))
    if sp_end < end:
        frames.append(fetch(k, "MODIS_NRT", meta["bbox"], sp_end + timedelta(days=1), end))
    df = pd.concat([f for f in frames if len(f)], ignore_index=True)
    if df.empty:
        raise SystemExit("No MODIS detections returned.")
    if "type" not in df:
        df["type"] = 0  # API rows carry no type; static sources are rare inside our study areas
    out = data.RAW / f"modis_{year}_{country}.csv"
    df.to_csv(out, index=False)
    print(f"{len(df):,} MODIS detections {start}..{end} -> {out.name}")
    data.build(country)


if __name__ == "__main__":
    main(sys.argv[1])

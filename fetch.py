"""Download NASA FIRMS yearly country archives (no API key needed).

    python fetch.py Kazakhstan

Files land in data/raw/. Interrupted downloads resume; finished ones are skipped.
"""
from __future__ import annotations

import sys
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import requests

BASE = "https://firms.modaps.eosdis.nasa.gov/data/country"
RAW = Path(__file__).parent / "data" / "raw"
# (url folder, file prefix, first year)
SENSORS = [("modis", "modis", 2000), ("viirs-snpp", "viirs-snpp", 2012)]
LAST_YEAR = 2025


def jobs(country: str):
    for folder, prefix, first in SENSORS:
        for year in range(first, LAST_YEAR + 1):
            name = f"{prefix}_{year}_{country}.csv"
            yield f"{BASE}/{folder}/{year}/{name}", RAW / name


def get(url: str, dest: Path, tries: int = 8) -> str:
    done = dest.with_suffix(".ok")
    if done.exists():
        return f"skip {dest.name}"
    part = dest.with_suffix(".part")
    for attempt in range(tries):
        have = part.stat().st_size if part.exists() else 0
        try:
            headers = {"Range": f"bytes={have}-"} if have else {}
            with requests.get(url, headers=headers, stream=True, timeout=120) as r:
                if r.status_code == 404:
                    return f"MISSING {dest.name}"
                if r.status_code == 416:  # already complete
                    break
                r.raise_for_status()
                mode = "ab" if r.status_code == 206 else "wb"
                with open(part, mode) as f:
                    for chunk in r.iter_content(1 << 16):
                        f.write(chunk)
            break
        except (requests.RequestException, OSError):
            time.sleep(5 * (attempt + 1))
    else:
        return f"FAILED {dest.name}"
    part.replace(dest)
    done.touch()
    return f"ok {dest.name} {dest.stat().st_size / 1e6:.1f} MB"


def main(country: str) -> None:
    RAW.mkdir(parents=True, exist_ok=True)
    with ThreadPoolExecutor(6) as pool:
        for msg in pool.map(lambda j: get(*j), jobs(country)):
            print(msg, flush=True)
    print("DONE", country, flush=True)


if __name__ == "__main__":
    main(sys.argv[1])

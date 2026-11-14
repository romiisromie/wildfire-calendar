"""Near-real-time fires: the last 7 days from NASA FIRMS regional files (no key needed).

S-NPP's 7-day files are currently empty, so 'right now' uses VIIRS on NOAA-20 (same instrument design, 375 m).
Files are cached for 3 hours.
"""
from __future__ import annotations

import time
from pathlib import Path

import pandas as pd
import requests

URL = "https://firms.modaps.eosdis.nasa.gov/data/active_fire/noaa-20-viirs-c2/csv/J1_VIIRS_C2_{}_7d.csv"
CACHE = Path(__file__).parent / "data" / "nrt"
MAX_AGE = 3 * 3600
# Rough boxes (west, south, east, north) fully inside FIRMS regional subsets; anything else uses the global file.
REGIONS = {"Russia_Asia": (26, 35, 180, 82), "South_America": (-92, -57, -32, 13), "Europe": (-25, 35, 45, 72)}


def region(bbox) -> str:
    w, s, e, n = bbox
    for name, (rw, rs, re, rn) in REGIONS.items():
        if w >= rw and s >= rs and e <= re and n <= rn:
            return name
    return "Global"


def _file(name: str) -> Path | None:
    f = CACHE / f"J1_{name}_7d.csv"
    if f.exists() and time.time() - f.stat().st_mtime < MAX_AGE:
        return f
    try:
        r = requests.get(URL.format(name), timeout=600)
        r.raise_for_status()
        CACHE.mkdir(parents=True, exist_ok=True)
        tmp = f.with_suffix(".tmp")
        tmp.write_bytes(r.content)
        tmp.replace(f)
    except requests.RequestException:
        pass  # keep using an older copy if there is one
    return f if f.exists() else None


def last7(bbox) -> tuple[pd.DataFrame, pd.Timestamp | None]:
    """Confident VIIRS (NOAA-20) detections of the last 7 days inside bbox, plus when the file was fetched."""
    f = _file(region(bbox))
    if f is None:
        return pd.DataFrame(columns=["lat", "lon", "date", "frp"]), None
    w, s, e, n = bbox
    d = pd.read_csv(f, usecols=["latitude", "longitude", "acq_date", "confidence", "frp"])
    d = d[(d.longitude >= w) & (d.longitude <= e) & (d.latitude >= s) & (d.latitude <= n)]
    d = d[d.confidence.astype(str).str.lower().str[0].isin(["n", "h"])]
    out = pd.DataFrame({"lat": d.latitude, "lon": d.longitude, "date": pd.to_datetime(d.acq_date), "frp": d.frp})
    return out.reset_index(drop=True), pd.Timestamp(f.stat().st_mtime, unit="s")

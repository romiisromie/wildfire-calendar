"""Near-real-time fires: the last 7 days from NASA FIRMS regional files (no key needed).

S-NPP's 7-day files are currently empty, so 'right now' uses VIIRS on NOAA-20 (same instrument design, 375 m).
Files are cached for 3 hours.
"""
from __future__ import annotations

import threading
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


_running: set[str] = set()
_lock = threading.Lock()


def _download(name: str, f: Path) -> None:
    try:
        r = requests.get(URL.format(name), timeout=600)
        r.raise_for_status()
        CACHE.mkdir(parents=True, exist_ok=True)
        tmp = f.with_suffix(f".{threading.get_ident()}.tmp")
        tmp.write_bytes(r.content)
        tmp.replace(f)
    except (requests.RequestException, OSError):
        pass  # keep using an older copy if there is one
    finally:
        with _lock:
            _running.discard(name)


def _file(name: str) -> Path | None:
    """Never blocks the page: a missing or stale file is refreshed in a background thread."""
    f = CACHE / f"J1_{name}_7d.csv"
    fresh = f.exists() and time.time() - f.stat().st_mtime < MAX_AGE
    if not fresh:
        with _lock:
            if name not in _running:
                _running.add(name)
                threading.Thread(target=_download, args=(name, f), daemon=True).start()
    return f if f.exists() else None


def loading(bbox) -> bool:
    return region(bbox) in _running


def stamp(bbox) -> float | None:
    """Modification time of the cached file for this area (a cache key); starts a refresh if needed."""
    f = _file(region(bbox))
    return f.stat().st_mtime if f else None


def last7(bbox) -> tuple[pd.DataFrame, pd.Timestamp | None, pd.Timestamp | None]:
    """Confident VIIRS (NOAA-20) detections inside bbox for the last 7 COMPLETE days in the file.

    The newest date in a FIRMS 7-day file is still being filled (a fraction of a normal day), so the window
    ends the day before it. Returns (detections, when the file was fetched, last day of the window).
    """
    f = _file(region(bbox))
    if f is None:
        return pd.DataFrame(columns=["lat", "lon", "date", "frp"]), None, None
    w, s, e, n = bbox
    d = pd.read_csv(f, usecols=["latitude", "longitude", "acq_date", "confidence", "frp"])
    if d.empty:
        return pd.DataFrame(columns=["lat", "lon", "date", "frp"]), None, None
    dates = pd.to_datetime(d.acq_date)
    end = dates.max().normalize() - pd.Timedelta(days=1)
    start = end - pd.Timedelta(days=6)
    d = d[(dates >= start) & (dates <= end)]
    d = d[(d.longitude >= w) & (d.longitude <= e) & (d.latitude >= s) & (d.latitude <= n)]
    d = d[d.confidence.astype(str).str.lower().str[0].isin(["n", "h"])]
    out = pd.DataFrame({"lat": d.latitude, "lon": d.longitude, "date": pd.to_datetime(d.acq_date), "frp": d.frp})
    return out.reset_index(drop=True), pd.Timestamp(f.stat().st_mtime, unit="s"), end

"""Turn raw FIRMS country CSVs into one compact, quickly filterable parquet file per country.

    python data.py Kazakhstan
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pyarrow.dataset as ds

ROOT = Path(__file__).parent / "data"
RAW = ROOT / "raw"
STORE = ROOT / "store"
AQUA_START = pd.Timestamp("2002-07-04")  # before this MODIS = Terra only
VIIRS_START = pd.Timestamp("2012-01-20")


def _read(path: Path) -> pd.DataFrame:
    d = pd.read_csv(path, usecols=lambda c: c in {
        "latitude", "longitude", "acq_date", "satellite", "instrument", "confidence", "frp", "type"})
    viirs = "viirs" in path.name
    conf = d["confidence"].astype(str).str.lower()
    if viirs:
        good = conf.isin(["n", "h", "nominal", "high"])
    else:
        good = pd.to_numeric(conf, errors="coerce").fillna(0) >= 30
    sat = d["satellite"].astype(str).str[0].str.upper()  # T(erra) / A(qua) / N(PP) / 1(=N20)
    return pd.DataFrame({
        "lat": d["latitude"].astype("float32"),
        "lon": d["longitude"].astype("float32"),
        "date": pd.to_datetime(d["acq_date"]),
        "sensor": np.where(viirs, "VIIRS", "MODIS"),
        "sat": np.where(viirs, "N", sat),
        "good": good.to_numpy(),
        "frp": d["frp"].astype("float32"),
        "type": d.get("type", pd.Series(0, index=d.index)).fillna(0).astype("int8"),
    })


def build(country: str) -> Path:
    files = sorted(RAW.glob(f"*_{country}.csv"))
    if not files:
        raise SystemExit(f"no raw files for {country}; run: python fetch.py {country}")
    df = pd.concat([_read(f) for f in files], ignore_index=True)
    df["sensor"] = df["sensor"].astype("category")
    df["sat"] = df["sat"].astype("category")
    df = df.sort_values(["lat", "lon"], ignore_index=True)  # row groups become spatially compact
    STORE.mkdir(parents=True, exist_ok=True)
    out = STORE / f"{country}.parquet"
    df.to_parquet(out, row_group_size=200_000, index=False)
    # A VIIRS gap = a day with no VIIRS detection anywhere in the country while MODIS still saw fires there
    # (instrument / processing outage, not a quiet day). Those days are filled from MODIS later.
    v = df.loc[df.sensor == "VIIRS", "date"]
    m = df.loc[(df.sensor == "MODIS") & (df.date >= v.min()) & (df.date <= v.max()), "date"].value_counts()
    gaps = pd.DatetimeIndex(m[m >= 5].index).difference(pd.DatetimeIndex(v.unique())).sort_values()
    meta = {"country": country, "rows": len(df), "start": str(df.date.min().date()), "end": str(df.date.max().date()),
            "bbox": [float(df.lon.min()), float(df.lat.min()), float(df.lon.max()), float(df.lat.max())],
            "viirs_gaps": [str(d.date()) for d in gaps]}
    (STORE / f"{country}.json").write_text(json.dumps(meta))
    print(f"{country}: {len(df):,} detections -> {out.name} ({out.stat().st_size / 1e6:.1f} MB), "
          f"VIIRS gap days: {len(gaps)}")
    return out


def countries() -> list[str]:
    return sorted(p.stem for p in STORE.glob("*.parquet"))


def meta(country: str) -> dict:
    return json.loads((STORE / f"{country}.json").read_text())


def load(country: str, bbox: tuple[float, float, float, float]) -> pd.DataFrame:
    """Detections inside (west, south, east, north)."""
    w, s, e, n = bbox
    f = ((ds.field("lon") >= w) & (ds.field("lon") <= e) & (ds.field("lat") >= s) & (ds.field("lat") <= n))
    return ds.dataset(STORE / f"{country}.parquet").to_table(filter=f).to_pandas()


def inside(lon: np.ndarray, lat: np.ndarray, ring: list[tuple[float, float]]) -> np.ndarray:
    """Point-in-polygon (even-odd rule) for a ring of (lon, lat) vertices."""
    lon, lat = np.asarray(lon), np.asarray(lat)
    hit = np.zeros(lon.shape, bool)
    x, y = np.array([p[0] for p in ring]), np.array([p[1] for p in ring])
    for i in range(len(ring)):
        x1, y1, x2, y2 = x[i - 1], y[i - 1], x[i], y[i]
        crosses = (y1 > lat) != (y2 > lat)
        with np.errstate(divide="ignore", invalid="ignore"):
            xc = x1 + (lat - y1) * (x2 - x1) / (y2 - y1)
        hit ^= crosses & (lon < xc)
    return hit


if __name__ == "__main__":
    build(sys.argv[1])

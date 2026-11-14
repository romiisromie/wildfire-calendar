"""Is the fire season shifting, and does fire weather matter here?

Weather: NASA POWER daily point data (MERRA-2, ~0.5°), no key needed.
"""
from __future__ import annotations

import json
from datetime import date, timedelta
from pathlib import Path

import numpy as np
import pandas as pd
import requests
from scipy import stats

POWER = "https://power.larc.nasa.gov/api/temporal/daily/point"
CACHE = Path(__file__).parent / "data" / "weather"


# ---------------- weather ----------------
def weather(lat: float, lon: float, end: date | None = None) -> pd.DataFrame:
    """Daily tmax (°C), precip (mm), rh (%), wind (m/s), vpd (kPa) and hdw = vpd × wind since 2000."""
    end = end or date.today() - timedelta(days=7)
    lat, lon = round(lat * 2) / 2, round(lon * 2) / 2  # POWER grid ~0.5°: nearby areas share one cache file
    f = CACHE / f"{lat}_{lon}_{end:%Y%m}.json"
    if not f.exists():
        r = requests.get(POWER, params={"parameters": "T2M_MAX,PRECTOTCORR,RH2M,WS2M", "community": "AG",
                                        "latitude": lat, "longitude": lon, "start": "20000101",
                                        "end": f"{end:%Y%m%d}", "format": "JSON"}, timeout=300)
        r.raise_for_status()
        CACHE.mkdir(parents=True, exist_ok=True)
        f.write_text(r.text)
    js = json.loads(f.read_text())
    p = js["properties"]["parameter"]
    d = pd.DataFrame({"tmax": p["T2M_MAX"], "precip": p["PRECTOTCORR"], "rh": p["RH2M"], "wind": p["WS2M"]})
    d.index = pd.to_datetime(d.index, format="%Y%m%d")
    d = d.where(d > -900)
    es = 0.6108 * np.exp(17.27 * d.tmax / (d.tmax + 237.3))
    d["vpd"] = es * (1 - d.rh.clip(0, 100) / 100)
    d["hdw"] = d.vpd * d.wind
    return d.dropna(how="all")


# ---------------- season timing ----------------
def _window(season: dict, pad: int = 4) -> np.ndarray:
    """Day-of-year numbers (1..365) covered by a season ± pad weeks; wraps across New Year."""
    weeks = (season["end"] - season["start"]) % 52 + 1 + 2 * pad
    first = (season["start"] - 1 - pad) * 7  # 0-based day of year, may be negative
    return (first + np.arange(min(weeks * 7, 365))) % 365 + 1


def timing(act: pd.Series, season: dict) -> pd.DataFrame:
    """Per season-year: day when 10% / 50% / 90% of the window's fire had happened (days from window start)."""
    days = _window(season)
    pos = {d: i for i, d in enumerate(days)}
    wraps = days[0] > days[-1]
    doy = np.minimum(act.index.dayofyear, 365)
    keep = np.isin(doy, days)
    s = act[keep]
    sy = s.index.year - ((doy[keep] < days[0]) & wraps).astype(int)  # Dec–Jan seasons belong to the start year
    rows = {}
    for y, g in s.groupby(sy):
        if len(g) < 0.9 * len(days) or g.sum() <= 0:
            continue
        i = np.array([pos[d] for d in np.minimum(g.index.dayofyear, 365)])
        order = np.argsort(i)
        c = np.cumsum(g.to_numpy()[order]) / g.sum()
        rows[y] = {q: int(i[order][np.searchsorted(c, f)]) for q, f in (("onset", .1), ("middle", .5), ("end", .9))}
        rows[y]["total"] = float(g.sum())
    return pd.DataFrame.from_dict(rows, orient="index").sort_index()


def trend(s: pd.Series) -> dict:
    s = s.dropna()
    if len(s) < 8:
        return {"slope": np.nan, "p": np.nan, "n": len(s)}
    slope = stats.theilslopes(s.to_numpy(), s.index.to_numpy())[0]
    p = stats.kendalltau(s.index.to_numpy(), s.to_numpy()).pvalue
    return {"slope": 10 * slope, "p": float(p), "n": len(s)}  # days per decade


def shift_report(act: pd.Series, modis_only: pd.Series, season: dict) -> dict:
    """Trends in onset/middle/end; 'robust' if MODIS alone (one sensor, 2003+) agrees in sign with p < 0.1."""
    t, tm = timing(act, season), timing(modis_only[modis_only.index.year >= 2003], season)
    out = {"timing": t, "window_start": int(_window(season)[0])}
    for q in ("onset", "middle", "end"):
        a = trend(t[q]) if len(t) else trend(pd.Series(dtype=float))
        b = trend(tm[q]) if len(tm) else trend(pd.Series(dtype=float))
        out[q] = {**a, "modis_slope": b["slope"], "modis_p": b["p"],
                  "robust": bool(a["p"] < .05 and b["p"] < .1 and np.sign(a["slope"]) == np.sign(b["slope"]))}
    return out


def doy_label(window_start: int, offset: float) -> str:
    return (pd.Timestamp("2001-01-01") + pd.Timedelta(days=int(window_start - 1 + round(offset)))).strftime("%d %b")


# ---------------- fire weather ----------------
def fire_weather(act: pd.Series, wx: pd.DataFrame, season: dict, boots: int = 200, seed: int = 0) -> dict | None:
    """Fire in the 3 days after hot-dry-windy vs calm-humid days, relative to the normal for those dates.

    HDW anomaly = hdw minus its day-of-year mean (so a normal summer day is not 'hot'). Expected fire on a date is
    the mean of the same date in all *other* years, so a year's own fire never explains itself.
    """
    days = set(_window(season, pad=0))
    a = act.reindex(wx.index)
    nxt = sum(a.shift(-k) for k in (1, 2, 3))  # fire in the following 3 days
    doy = np.minimum(wx.index.dayofyear, 365)
    hdw_anom = wx.hdw - wx.hdw.groupby(doy).transform("mean").rolling(15, center=True, min_periods=1).mean()
    df = pd.DataFrame({"y": wx.index.year, "doy": doy, "nxt": nxt, "hdw": hdw_anom}).dropna()
    df = df[df.doy.isin(days)]
    if df.y.nunique() < 8 or df.nxt.sum() <= 0:
        return None
    tot = df.groupby("doy").nxt.agg(["sum", "count"])
    j = df.doy.map(tot["sum"]) - df.nxt
    df["exp"] = j / (df.doy.map(tot["count"]) - 1)
    lo, hi = df.hdw.quantile([.2, .8])
    df["cls"] = np.where(df.hdw >= hi, "hot", np.where(df.hdw <= lo, "calm", "normal"))

    def ratio(d, c):
        x = d[d.cls == c]
        return x.nxt.sum() / x.exp.sum() if x.exp.sum() > 0 else np.nan

    res = {c: ratio(df, c) for c in ("hot", "calm")}
    rng = np.random.default_rng(seed)
    years = df.y.unique()
    bs = {"hot": [], "calm": []}
    groups = {y: g for y, g in df.groupby("y")}
    for _ in range(boots):
        d = pd.concat([groups[y] for y in rng.choice(years, len(years))])
        for c in bs:
            bs[c].append(ratio(d, c))
    for c in bs:
        res[f"{c}_ci"] = tuple(np.nanpercentile(bs[c], [5, 95]))
    res["years"] = len(years)
    res["thresholds"] = (float(lo), float(hi))
    return res


def recent_days(wx: pd.DataFrame, n: int = 60) -> pd.DataFrame:
    """Last n days classified hot-dry-windy / normal / calm-humid with the same anomaly rule."""
    doy = np.minimum(wx.index.dayofyear, 365)
    clim = wx.hdw.groupby(doy).transform("mean").rolling(15, center=True, min_periods=1).mean()
    anom = (wx.hdw - clim).dropna()
    lo, hi = anom.quantile([.2, .8])
    t = anom.iloc[-n:].to_frame("anom")
    t["cls"] = np.where(t.anom >= hi, "hot-dry-windy", np.where(t.anom <= lo, "calm-humid", "normal"))
    return t

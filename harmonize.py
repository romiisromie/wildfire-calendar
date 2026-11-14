"""Put MODIS (2000-) and VIIRS (2012-) on one scale: 'VIIRS-equivalent' activity.

VIIRS (375 m) sees roughly 2x more fire than MODIS (1 km), and the ratio depends on season and landscape.
So for each area we learn a month-by-month factor k = VIIRS / MODIS from the years both flew, test it by
leaving each year out, and report how much the user can trust old-vs-new comparisons.
"""
from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
import pandas as pd

from data import AQUA_START

MEASURES = {"cells": "Active 0.1° cells", "count": "Hotspot detections", "frp": "Fire radiative power (MW)"}
FIRST_FULL_OVERLAP = 2013  # VIIRS starts 20 Jan 2012


def daily(df: pd.DataFrame, start, end, measure: str = "cells", gaps=()) -> pd.DataFrame:
    """Daily activity per sensor. Columns: modis, terra (MODIS from Terra only), viirs (NaN on gap days)."""
    idx = pd.date_range(start, end, freq="D")
    d = df[df.good & (df.type == 0)]  # confident detections of vegetation fires (no volcanoes/industry)

    def agg(sub):
        if sub.empty:
            return pd.Series(0.0, index=idx)
        if measure == "cells":
            key = pd.DataFrame({"date": sub.date, "x": np.floor(sub.lon * 10), "y": np.floor(sub.lat * 10)})
            s = key.drop_duplicates().groupby("date").size()
        elif measure == "frp":
            s = sub.groupby("date").frp.sum()
        else:
            s = sub.groupby("date").size()
        return s.reindex(idx, fill_value=0).astype(float)

    m = d[d.sensor == "MODIS"]
    v = d[d.sensor == "VIIRS"]
    out = pd.DataFrame({"modis": agg(m), "terra": agg(m[m.sat == "T"]), "viirs": agg(v)}, index=idx)
    first_v = pd.Timestamp("2012-01-20")
    out.loc[out.index < first_v, "viirs"] = np.nan
    out.loc[out.index.isin(pd.DatetimeIndex(gaps)), "viirs"] = np.nan
    return out


def _shrunk_ratio(num: pd.Series, den: pd.Series) -> tuple[pd.Series, float]:
    """Monthly ratio of sums, pulled toward the all-year ratio when a month has little fire."""
    g = num.sum() / den.sum() if den.sum() > 0 else 1.0
    prior = max(den.sum() / 24, 1e-9)  # weight of the global ratio = half an average month
    k = (num + g * prior) / (den + prior)
    return k.reindex(range(1, 13)).fillna(g), float(g)


@dataclass
class Fit:
    k: pd.Series            # month -> VIIRS / MODIS
    k_global: float
    k_terra: pd.Series      # month -> MODIS(Terra+Aqua) / MODIS(Terra), for 2000-07/2002
    years: list = field(default_factory=list)


def fit(dly: pd.DataFrame, exclude: int | None = None) -> Fit:
    o = dly[(dly.index.year >= FIRST_FULL_OVERLAP) & dly.viirs.notna()]
    o = o[o.index.year != exclude] if exclude else o
    by = o.groupby(o.index.month)
    k, g = _shrunk_ratio(by.viirs.sum(), by.modis.sum())
    t = dly[(dly.index.year >= 2003) & (dly.index.year <= 2011)]
    bt = t.groupby(t.index.month)
    kt, _ = _shrunk_ratio(bt.modis.sum(), bt.terra.sum())
    return Fit(k=k, k_global=g, k_terra=kt, years=sorted(set(o.index.year)))


def harmonized(dly: pd.DataFrame, f: Fit) -> pd.Series:
    """One continuous VIIRS-equivalent series: VIIRS where it exists, MODIS x k otherwise."""
    month = dly.index.month
    est = dly.modis * f.k.reindex(month).to_numpy()
    terra_only = dly.index < AQUA_START
    est[terra_only] = est[terra_only] * f.k_terra.reindex(month[terra_only]).to_numpy()
    return dly.viirs.fillna(est).rename("activity")


def validate(dly: pd.DataFrame) -> dict:
    """Leave-one-year-out: predict each overlap year's monthly VIIRS totals from MODIS alone."""
    o = dly[(dly.index.year >= FIRST_FULL_OVERLAP) & dly.viirs.notna()]
    rows = []
    for y in sorted(set(o.index.year)):
        f = fit(dly, exclude=y)
        oy = o[o.index.year == y]
        by = oy.groupby(oy.index.month)
        act, mod = by.viirs.sum(), by.modis.sum()
        rows.append(pd.DataFrame({"year": y, "month": act.index, "viirs": act.values,
                                  "pred_monthly_k": (mod * f.k.reindex(mod.index)).values,
                                  "pred_one_k": (mod * f.k_global).values, "modis_raw": mod.values}))
    t = pd.concat(rows, ignore_index=True) if rows else pd.DataFrame()

    def err(col):
        return float(100 * (t[col] - t.viirs).abs().sum() / t.viirs.sum()) if len(t) and t.viirs.sum() > 0 else np.nan

    per_year = (t.groupby("year").apply(lambda g: pd.Series({
        "VIIRS": g.viirs.sum(), "MODIS x k": g.pred_monthly_k.sum(),
        "monthly error %": 100 * (g.pred_monthly_k - g.viirs).abs().sum() / max(g.viirs.sum(), 1e-9)}),
        include_groups=False) if len(t) else pd.DataFrame())
    active_years = int((t.groupby("year").viirs.sum() > 0).sum()) if len(t) else 0
    return {"table": t, "per_year": per_year, "err": err("pred_monthly_k"), "err_one_k": err("pred_one_k"),
            "err_raw": err("modis_raw"), "years": active_years,
            "total": float(t.viirs.sum()) if len(t) else 0.0}


def trust(v: dict, measure: str = "cells") -> tuple[str, str]:
    """Plain-language trust label for comparing pre-2012 (MODIS-based) and recent (VIIRS) years."""
    small = {"cells": 300, "count": 500, "frp": 5000}[measure]
    if v["years"] < 5 or v["total"] < small:
        return "Insufficient", "Too little fire in 2013–2025 to test the conversion here. Seasons are still valid."
    e = v["err"]
    if e < 20:
        return "High", f"Old and new years are comparable (held-out error {e:.0f}%)."
    if e < 40:
        return "Medium", f"Seasons and big changes are reliable; small year-to-year differences are not ({e:.0f}%)."
    return "Low", f"Use for timing, not for amounts across 2012 ({e:.0f}% error)."

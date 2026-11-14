"""Calendar views and season statistics on the harmonized daily series."""
from __future__ import annotations

import numpy as np
import pandas as pd

MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]


def monthly(act: pd.Series) -> pd.DataFrame:
    """year x month table of total activity (NaN for months outside the record)."""
    s = act.groupby([act.index.year, act.index.month]).sum()
    t = s.unstack().reindex(columns=range(1, 13))
    first, last = act.index.min(), act.index.max()
    for y in t.index:
        for m in t.columns:
            p = pd.Period(year=y, month=m, freq="M")
            if p.start_time < first or p.end_time.normalize() > last:  # month not fully covered
                t.loc[y, m] = np.nan
    return t


def weekly(act: pd.Series) -> pd.DataFrame:
    """year x week-of-year (1..52) mean daily activity x 7; day 365/366 folded into week 52."""
    wk = np.minimum((act.index.dayofyear - 1) // 7 + 1, 52)
    return act.groupby([act.index.year, wk]).mean().mul(7).unstack()


def climatology(wk: pd.DataFrame, exclude: int | None = None) -> pd.DataFrame:
    w = wk.drop(index=exclude) if exclude in wk.index else wk
    full = w.dropna(thresh=48)  # use only (nearly) complete years
    return pd.DataFrame({"median": full.median(), "p10": full.quantile(0.1), "p90": full.quantile(0.9),
                         "mean": full.mean()})


def week_label(w: int) -> str:
    return (pd.Timestamp("2001-01-01") + pd.Timedelta(days=7 * (int(w) - 1))).strftime("%d %b")


def fire_seasons(clim: pd.DataFrame, min_share: float = 5.0) -> list[dict]:
    """Runs of weeks where typical activity is above the yearly-average week (circular, so Dec-Jan joins)."""
    m = clim["mean"].reindex(range(1, 53)).fillna(0).to_numpy()
    if m.sum() <= 0:
        return []
    hot = m > m.mean()
    if hot.all():
        return [{"start": 1, "end": 52, "peak": int(m.argmax()) + 1, "share": 100.0}]
    shift = int(np.argmin(hot))  # start scanning at a quiet week so no run is cut in two
    runs, cur = [], []
    for i in range(52):
        j = (shift + i) % 52
        if hot[j]:
            cur.append(j)
        elif cur:
            runs.append(cur)
            cur = []
    if cur:
        runs.append(cur)
    out = []
    for r in runs:
        share = 100 * m[r].sum() / m.sum()
        if share >= min_share:
            out.append({"start": r[0] + 1, "end": r[-1] + 1, "peak": int(r[int(np.argmax(m[r]))]) + 1,
                        "share": float(share)})
    return sorted(out, key=lambda s: -s["share"])


def season_label(s: dict) -> str:
    end = pd.Timestamp("2001-01-01") + pd.Timedelta(days=7 * s["end"] - 1)
    return f"{week_label(s['start'])} – {end:%d %b}"


def latest_month(act: pd.Series, mon: pd.DataFrame) -> dict | None:
    """Most recent complete month against the same month in all earlier years."""
    last = act.index.max()
    p = pd.Period(last, "M")
    if last < p.end_time.normalize():
        p -= 1
    y, m = p.year, p.month
    if y not in mon.index or pd.isna(mon.loc[y, m]):
        return None
    hist = mon.loc[mon.index < y, m].dropna()
    if len(hist) < 5:
        return None
    v, med = float(mon.loc[y, m]), float(hist.median())
    return {"year": y, "month": m, "value": v, "median": med, "ratio": v / med if med > 0 else np.nan,
            "rank": int(1 + (hist > v).sum()), "n": len(hist) + 1,
            "p10": float(hist.quantile(0.1)), "p90": float(hist.quantile(0.9))}


def anomalies(wk: pd.DataFrame, clim_by_year) -> pd.DataFrame:
    """Weeks far above normal for their time of year (normal learned without that year)."""
    rows = []
    for y in wk.index:
        c = clim_by_year(y)
        typical_peak = c["median"].max()
        for w, v in wk.loc[y].dropna().items():
            med, p90 = c.loc[w, "median"], c.loc[w, "p90"]
            if v > p90 and v >= 3 * max(med, 1e-9) and v >= 0.1 * typical_peak and v > 0:
                rows.append({"week of": f"{week_label(w)} {y}", "year": y, "week": w, "activity": v,
                             "normal": med, "x normal": v / med if med > 0 else np.inf})
    return pd.DataFrame(rows).sort_values("activity", ascending=False) if rows else pd.DataFrame()


def yearly(act: pd.Series) -> pd.DataFrame:
    s = act.groupby(act.index.year).agg(["sum", "count"])
    s = s[s["count"] >= 330]
    return s.rename(columns={"sum": "activity", "count": "days"})

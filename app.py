"""Wildfire Calendar: one 25-year fire record from MODIS + VIIRS for any area you draw.

    streamlit run app.py
"""
from __future__ import annotations

import io
import math

import folium
import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from folium.plugins import Draw, HeatMap
from streamlit_folium import st_folium

import data
import harmonize as H
import seasons as S
import style as U

st.set_page_config(page_title="Wildfire Calendar", page_icon="🔥", layout="wide", initial_sidebar_state="collapsed")
st.markdown(U.CSS, unsafe_allow_html=True)

PRESETS = {
    "Kazakhstan": {
        "Kostanay steppe": (60.0, 48.5, 66.5, 54.5),
        "Naurzum reserve": (63.5, 51.0, 65.5, 52.0),
        "Arakaragai pine forest": (63.5, 52.0, 64.5, 53.0),
    },
    "Argentina": {
        "Paraná Delta wetlands": (-60.9, -34.3, -58.3, -32.0),
        "Corrientes & Iberá": (-59.7, -30.8, -55.6, -27.2),
        "Córdoba hills": (-65.5, -32.5, -64.0, -30.0),
        "Comarca Andina forest": (-71.8, -42.3, -71.2, -41.8),
    },
}
# Fires reported in the news / agency bulletins: independent check that the record sees real events.
EVENTS = [
    ("2015-08-03", 52.6, 64.2, "Kazakhstan", "Kostanay steppe fires, Aug 2015"),
    ("2022-09-03", 52.6, 64.0, "Kazakhstan", "Arakaragai forest fire, Sep 2022"),
    ("2020-08-18", -33.0, -59.5, "Argentina", "Paraná Delta wetland fires, Aug 2020"),
    ("2020-10-04", -31.0, -64.6, "Argentina", "Córdoba hills fires, Oct 2020"),
    ("2021-03-09", -42.0, -71.5, "Argentina", "Las Golondrinas (Chubut) fire, Mar 2021"),
    ("2022-02-16", -28.5, -57.5, "Argentina", "Corrientes fires, Feb 2022"),
]
TRUST = {"High": ("#7fb069", "solid"), "Medium": (U.FLAME, "careful"), "Low": (U.EMBER, "timing only"),
         "Insufficient": (U.MUTED, "too little fire to test")}
SCALES = {"Burn (dark → bright)": U.BURN, "Cividis": "cividis"}

countries = data.countries()
if not countries:
    st.error("No data yet. Run `python fetch.py Kazakhstan` and `python data.py Kazakhstan` first.")
    st.stop()

# ---------------- header ----------------
st.markdown(U.brand(), unsafe_allow_html=True)
st.markdown(U.orbit(), unsafe_allow_html=True)

# ---------------- settings (rarely changed) ----------------
with st.sidebar:
    st.markdown(U.section("⚙", "Settings"), unsafe_allow_html=True)
    measure = st.selectbox("Activity measure", list(H.MEASURES), format_func=H.MEASURES.get,
                           help="Active 0.1° cells per day changes least between the two sensors (default).")
    scale_name = st.radio("Calendar colours", list(SCALES),
                          help="Both scales get brighter with more fire, so they read in greyscale and for colour-blind users.")
    scale = SCALES[scale_name]

# ---------------- area picker ----------------
c1, c2, c3 = st.columns([1.1, 1.6, 3.3], vertical_alignment="bottom")
country = c1.selectbox("Country", countries)
meta = data.meta(country)
mode = c2.segmented_control("Choose area", ["Example", "Draw", "Point"], default="Example",
                            help="Example: ready-made areas · Draw: rectangle or polygon on the map · "
                                 "Point: coordinates and a radius") or "Example"
ring, name = None, None
if mode == "Example":
    presets = PRESETS.get(country) or {"Whole country": tuple(meta["bbox"])}
    name = c3.pills("Area", list(presets), default=list(presets)[0], label_visibility="hidden") or list(presets)[0]
    bbox = presets[name]
elif mode == "Point":
    b0 = meta["bbox"]
    p1, p2, p3 = c3.columns(3)
    lat = p1.number_input("Latitude", -90.0, 90.0, round((b0[1] + b0[3]) / 2, 2), format="%.3f")
    lon = p2.number_input("Longitude", -180.0, 180.0, round((b0[0] + b0[2]) / 2, 2), format="%.3f")
    km = p3.number_input("Radius, km", 5, 500, 50, step=5)
    dlat, dlon = km / 111.0, km / (111.0 * max(math.cos(math.radians(lat)), 0.05))
    bbox = (lon - dlon, lat - dlat, lon + dlon, lat + dlat)
    ring = [(lon + dlon * math.cos(a), lat + dlat * math.sin(a)) for a in np.linspace(0, 2 * math.pi, 64)]
    name = f"{km} km around {lat:.2f}°, {lon:.2f}°"
else:
    ring = st.session_state.get(f"ring_{country}")
    if ring:
        xs, ys = [p[0] for p in ring], [p[1] for p in ring]
        bbox = (min(xs), min(ys), max(xs), max(ys))
        name = "Your drawn area"
        if c3.button("Clear drawing"):
            st.session_state.pop(f"ring_{country}")
            st.rerun()
    else:
        bbox = tuple(meta["bbox"])
        c3.markdown('<div class="wc-note">Use the ▭ or ⬠ tool on the map’s left edge to outline an area.</div>',
                    unsafe_allow_html=True)


# ---------------- analysis (cached) ----------------
@st.cache_data(show_spinner="Reading hotspots…", max_entries=16)
def load_area(country, bbox, ring):
    df = data.load(country, bbox)
    if ring:
        df = df[data.inside(df.lon.to_numpy(), df.lat.to_numpy(), list(ring))]
    return df.reset_index(drop=True)


@st.cache_data(show_spinner="Harmonizing MODIS and VIIRS…", max_entries=32)
def analyse(country, bbox, ring, measure):
    df = load_area(country, bbox, ring)
    m = data.meta(country)
    dly = H.daily(df, "2000-11-01", m["end"], measure, m["viirs_gaps"])
    f = H.fit(dly)
    return df, dly, f, H.harmonized(dly, f), H.validate(dly)


res = None
if name:
    ring_key = tuple(map(tuple, ring)) if ring else None
    res = analyse(country, tuple(bbox), ring_key, measure)
    if res[0].empty or res[3].sum() == 0:
        res = None
        st.warning("No fire detections in this area. Try a larger one.")

# ---------------- map + readout ----------------
left, right = st.columns([3, 2], gap="large")
with left:
    w, s_, e, n = bbox
    esri = "https://server.arcgisonline.com/ArcGIS/rest/services/Canvas/{}/MapServer/tile/{{z}}/{{y}}/{{x}}"
    fm = folium.Map(location=[(s_ + n) / 2, (w + e) / 2], tiles=esri.format("World_Dark_Gray_Base"), zoom_start=6,
                    attr="Tiles &copy; Esri &mdash; Esri, HERE, Garmin, &copy; OpenStreetMap contributors")
    folium.TileLayer(esri.format("World_Dark_Gray_Reference"), attr="Esri", overlay=True, opacity=0.8).add_to(fm)
    if res is not None:
        df = res[0]
        recent = df[(df.sensor == "VIIRS") & df.good & (df.date.dt.year >= int(meta["end"][:4]) - 2)]
        pts = recent[["lat", "lon"]].sample(min(len(recent), 20000), random_state=1).to_numpy().tolist()
        if pts:
            HeatMap(pts, radius=6, blur=8, min_opacity=0.35,
                    gradient={0.2: "#7a2a0c", 0.5: "#e8590c", 0.8: "#ffa630", 1.0: "#fff1b8"}).add_to(fm)
    if name:
        style = dict(color=U.FLAME, weight=1.5, fill=False, dash_array="5 4")
        if ring:
            folium.Polygon([(y, x) for x, y in ring], **style).add_to(fm)
        else:
            folium.Rectangle([(s_, w), (n, e)], **style).add_to(fm)
    fm.fit_bounds([(s_, w), (n, e)])
    Draw(draw_options={"polyline": False, "circle": False, "marker": False, "circlemarker": False,
                       "polygon": {"shapeOptions": {"color": U.FLAME}},
                       "rectangle": {"shapeOptions": {"color": U.FLAME}}},
         edit_options={"edit": False}).add_to(fm)
    out = st_folium(fm, height=430, use_container_width=True, returned_objects=["last_active_drawing"],
                    key=f"map_{country}_{mode}_{name}")
    drawing = (out or {}).get("last_active_drawing")
    if drawing and drawing.get("geometry", {}).get("type") == "Polygon":
        new = [tuple(p) for p in drawing["geometry"]["coordinates"][0]]
        if new != st.session_state.get(f"ring_{country}"):
            st.session_state[f"ring_{country}"] = new
            st.session_state["pending_draw"] = mode != "Draw"
            st.rerun()
    if st.session_state.pop("pending_draw", False):
        st.info("Area drawn. Switch **Choose area** to **Draw** to analyse it.")
    if res is not None:
        st.markdown(f'<div class="wc-note">Glow = VIIRS hotspots of the last three years. '
                    f'Dashed line = analysed area.</div>', unsafe_allow_html=True)

if res is None:
    with right:
        st.markdown('<div class="wc-kicker">No area yet</div><div class="wc-area">Outline a place on the map</div>'
                    '<div class="wc-lede">Pick an example, draw a shape, or enter coordinates. You get its fire '
                    'calendar since 2000, how this year compares, and how far you can trust old-vs-new numbers.</div>',
                    unsafe_allow_html=True)
    st.stop()

df, dly, fit, act, val = res
level, why = H.trust(val, measure)
mon = S.monthly(act)
wk = S.weekly(act)
last_year = int(act.index.max().year)
clim = S.climatology(wk, exclude=last_year)
seas = S.fire_seasons(clim)
lm = S.latest_month(act, mon)
yr = S.yearly(act)
unit = H.MEASURES[measure].lower()

with right:
    st.markdown(f'<div class="wc-kicker">{U.esc(country)} · {meta["start"][:4]}–{meta["end"][:4]}</div>'
                f'<div class="wc-area">{U.esc(name)}</div>', unsafe_allow_html=True)
    lede = []
    if seas:
        lede.append(f"Land here burns mostly <em>{S.season_label(seas[0])}</em> "
                    f"({seas[0]['share']:.0f}% of a year’s fire)"
                    + (f", with a second season <em>{S.season_label(seas[1])}</em>" if len(seas) > 1 else "") + ".")
    if lm and np.isfinite(lm["ratio"]):
        r = lm["ratio"]
        word = "far more than" if r > 2 else "more than" if r > 1.25 else "less than" if r < 0.8 else "about as much as"
        lede.append(f"{S.MONTHS[lm['month'] - 1]} {lm['year']} burned <em>{word} usual</em> ({r:.1f}× the median).")
    if len(yr) >= 10:
        a, b = yr.activity.loc[:2010].mean(), yr.activity.loc[2016:].mean()
        if a > 0 and level in ("High", "Medium"):
            ch = 100 * (b / a - 1)
            lede.append(f"Since the 2000s, yearly fire is <em>{'down' if ch < 0 else 'up'} {abs(ch):.0f}%</em>.")
    st.markdown(f'<div class="wc-lede">{" ".join(lede)}</div>', unsafe_allow_html=True)

    color, short = TRUST[level]
    st.markdown(U.readout("Old vs new years comparable?", f"{level}", f"{short} · {why}", dot=color),
                unsafe_allow_html=True)
    if lm:
        mname = f"{S.MONTHS[lm['month'] - 1]} {lm['year']}"
        if np.isfinite(lm["ratio"]):
            st.markdown(U.readout(f"{mname} vs median", f"{lm['ratio']:.2f}×",
                                  f"rank {lm['rank']} of {lm['n']} years · usual {lm['p10']:,.0f}–{lm['p90']:,.0f}"),
                        unsafe_allow_html=True)
        else:
            st.markdown(U.readout(f"{mname}", f"{lm['value']:,.0f}",
                                  f"{unit} · this month usually has almost no fire here"), unsafe_allow_html=True)
    if len(yr):
        top = int(yr.activity.idxmax())
        st.markdown(U.readout("Worst year on record", str(top),
                              f"{yr.activity.max() / yr.activity.median():.1f}× a typical year"),
                    unsafe_allow_html=True)
    st.markdown(U.readout("Hotspots analysed", f"{int(df.good.sum()):,}",
                          f"{(df.sensor == 'MODIS').sum():,} MODIS · {(df.sensor == 'VIIRS').sum():,} VIIRS"),
                unsafe_allow_html=True)

tabs = st.tabs(["Calendar", "This year", "Seasons & events", "Harmonization", "Download", "Method"])

# ---------------- calendar ----------------
with tabs[0]:
    a1, a2 = st.columns([1, 3], vertical_alignment="center")
    view = a1.segmented_control("Grid", ["Months", "Weeks"], default="Months", label_visibility="collapsed") or "Months"
    years = a2.slider("Years", int(mon.index.min()), last_year, (int(mon.index.min()), last_year),
                      label_visibility="collapsed")
    if view == "Months":
        t = mon.loc[years[0]:years[1]]
        z, xs = t.to_numpy(), S.MONTHS
    else:
        t = wk.loc[years[0]:years[1]].reindex(columns=range(1, 53))
        z, xs = t.to_numpy(), [S.week_label(i) for i in t.columns]
    zl = np.log10(z + 1)
    top = max(1.0, float(np.nanmax(zl)))
    tv = [v for v in range(0, 7) if v <= top + 0.01]
    hover = np.vectorize(lambda v: "not observed" if np.isnan(v) else f"{v:,.0f}")(z)
    fig = go.Figure(go.Heatmap(z=zl, x=xs, y=t.index, colorscale=scale, text=hover, xgap=2, ygap=2,
                               zmin=0, zmax=top, hovertemplate="%{x} %{y}<br><b>%{text}</b> " + unit + "<extra></extra>",
                               colorbar=dict(title=dict(text=unit, side="right"), tickvals=tv, thickness=10,
                                             ticktext=[f"{10 ** v - 1:,.0f}" if v < 3 else f"{10 ** v / 1000:,.0f}k"
                                                       for v in tv], outlinewidth=0)))
    if years[0] <= 2011 < years[1]:
        fig.add_hline(y=2011.5, line=dict(color=U.MUTED, width=1, dash="dot"))
        fig.add_annotation(x=1.0, xref="paper", y=2011.5, text="VIIRS starts ↓", showarrow=False, yshift=-9,
                           xanchor="right", font=dict(size=10, color=U.MUTED))
    fig.update_layout(height=max(380, 24 * len(t) + 60), margin=dict(t=30, l=10, r=10, b=10),
                      yaxis=dict(autorange="reversed", dtick=1, title=None, showgrid=False),
                      xaxis=dict(side="top", title=None, showgrid=False))
    st.plotly_chart(fig, width="stretch", config={"displayModeBar": False})
    st.markdown('<div class="wc-note">Brighter = more fire (log scale). Before 2012 values are MODIS converted to '
                'VIIRS units; empty cells were not fully observed.</div>', unsafe_allow_html=True)

# ---------------- this year ----------------
with tabs[1]:
    y = last_year
    cur = wk.loc[y].reindex(range(1, 53)) if y in wk.index else pd.Series(np.nan, index=range(1, 53))
    lo, hi, med = (clim[c].reindex(range(1, 53)) for c in ("p10", "p90", "median"))
    xl = [S.week_label(i) for i in range(1, 53)]
    colors = np.where(cur > hi, U.EMBER, np.where(cur < lo, U.COOL, "#8a5a3c"))
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=xl, y=hi, line=dict(width=0), showlegend=False, hoverinfo="skip"))
    fig.add_trace(go.Scatter(x=xl, y=lo, fill="tonexty", line=dict(width=0), fillcolor="rgba(236,227,212,0.08)",
                             name="usual range (10–90%)", hoverinfo="skip"))
    fig.add_trace(go.Bar(x=xl, y=cur, name=str(y), marker_color=colors, marker_line_width=0,
                         hovertemplate="week of %{x}: %{y:,.0f}<extra></extra>"))
    fig.add_trace(go.Scatter(x=xl, y=med, line=dict(color=U.INK, dash="dot", width=1.2), name="median year",
                             hovertemplate="median: %{y:,.0f}<extra></extra>"))
    fig.update_layout(height=420, margin=dict(t=10, b=10), bargap=0.15, yaxis_title=f"{unit} per week",
                      xaxis=dict(tickmode="array", tickvals=xl[::4], tickangle=0),
                      legend=dict(orientation="h", y=1.06, x=0))
    st.plotly_chart(fig, width="stretch", config={"displayModeBar": False})
    st.markdown(f'<div class="wc-note"><span style="color:{U.EMBER}">■</span> above the usual range · '
                f'<span style="color:#8a5a3c">■</span> within · <span style="color:{U.COOL}">■</span> below. '
                f'“Usual” = complete years 2000–{y - 1}.</div>', unsafe_allow_html=True)

# ---------------- seasons & events ----------------
with tabs[2]:
    st.markdown(U.section("A", "Fire seasons"), unsafe_allow_html=True)
    if seas:
        st.dataframe(pd.DataFrame([{"season": S.season_label(x), "peak week": S.week_label(x["peak"]),
                                    "share of yearly fire": f"{x['share']:.0f}%"} for x in seas]),
                     hide_index=True)
    st.markdown(U.section("B", "Documented fires — does the satellite record see them?"), unsafe_allow_html=True)
    ev = [x for x in EVENTS if x[3] == country and bbox[0] <= x[2] <= bbox[2] and bbox[1] <= x[1] <= bbox[3]]
    if ev:
        v = df[(df.sensor == "VIIRS") & df.good]
        rows = []
        for ds_, la, lo_, _, label in ev:
            t0 = pd.Timestamp(ds_)
            counts = {yy: int(v.date.between(t0.replace(year=yy) - pd.Timedelta(days=3),
                                             t0.replace(year=yy) + pd.Timedelta(days=3)).sum())
                      for yy in range(2013, 2026)}
            me = counts[t0.year]
            rank = 1 + sum(c > me for yy, c in counts.items() if yy != t0.year)
            rows.append({"reported fire": label, "hotspots ±3 days": me,
                         "same dates, typical year": int(np.median([c for yy, c in counts.items() if yy != t0.year])),
                         "result": "highest of 2013–2025" if rank == 1 and me else f"rank {rank} of 13"})
        st.dataframe(pd.DataFrame(rows), hide_index=True)
    else:
        st.markdown('<div class="wc-note">No documented fire inside this area.</div>', unsafe_allow_html=True)
    st.markdown(U.section("C", "Weeks far above normal for their time of year"), unsafe_allow_html=True)
    cache = {}
    an = S.anomalies(wk, lambda yy: cache.setdefault(yy, S.climatology(wk, exclude=yy)))
    if an.empty:
        st.markdown('<div class="wc-note">No strong anomalies.</div>', unsafe_allow_html=True)
    else:
        st.dataframe(an.head(15).drop(columns=["year", "week"]).round(1), hide_index=True)

# ---------------- harmonization ----------------
with tabs[3]:
    st.markdown(U.section("1", "How wrong is MODIS × factor on years it never saw?"), unsafe_allow_html=True)
    errs = pd.DataFrame({"method": ["raw MODIS", "one factor", "monthly factor (used)"],
                         "error": [val["err_raw"], val["err_one_k"], val["err"]]})
    fig = go.Figure(go.Bar(x=errs.error, y=errs.method, orientation="h", text=[f"{e:.0f}%" for e in errs.error],
                           textposition="outside", marker_color=[U.LINE, "#8a5a3c", U.EMBER],
                           hoverinfo="skip"))
    fig.update_layout(height=170, margin=dict(t=0, b=0, l=0, r=40), xaxis=dict(title="held-out monthly error, %",
                      range=[0, max(100, errs.error.max() * 1.15)]), yaxis=dict(title=None))
    st.plotly_chart(fig, width="stretch", config={"displayModeBar": False})
    st.markdown('<div class="wc-note">For each year 2013–2025 the factor is learned from the other years only, '
                'then that year’s monthly VIIRS totals are predicted from MODIS. '
                'Error = Σ|predicted − actual| / Σ actual.</div>', unsafe_allow_html=True)
    st.markdown(U.section("2", "VIIRS sees this many times more than MODIS, by month"), unsafe_allow_html=True)
    fig = go.Figure(go.Bar(x=S.MONTHS, y=fit.k.values, marker_color=U.FLAME, marker_line_width=0,
                           hovertemplate="%{x}: ×%{y:.2f}<extra></extra>"))
    fig.add_hline(y=fit.k_global, line=dict(color=U.INK, dash="dot", width=1),
                  annotation_text=f"all-year ×{fit.k_global:.2f}", annotation_font_color=U.MUTED)
    fig.update_layout(height=260, margin=dict(t=10, b=10))
    st.plotly_chart(fig, width="stretch", config={"displayModeBar": False})
    st.markdown(U.section("3", "Overlap years: VIIRS vs converted MODIS"), unsafe_allow_html=True)
    o = dly[dly.index.year >= 2013].copy()
    o["conv"] = o.modis * fit.k.reindex(o.index.month).to_numpy()
    om = o.resample("MS")[["viirs", "conv", "modis"]].sum()
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=om.index, y=om.modis, name="MODIS raw", line=dict(color="#6b5a4c", width=1)))
    fig.add_trace(go.Scatter(x=om.index, y=om.viirs, name="VIIRS", line=dict(color=U.EMBER, width=2)))
    fig.add_trace(go.Scatter(x=om.index, y=om.conv, name="MODIS × factor", line=dict(color=U.FLAME, width=1.5,
                                                                                         dash="dot")))
    fig.update_layout(height=320, margin=dict(t=10, b=10), yaxis_title=f"{unit} per month",
                      legend=dict(orientation="h", y=1.08, x=0))
    st.plotly_chart(fig, width="stretch", config={"displayModeBar": False})

# ---------------- download ----------------
with tabs[4]:
    head = (f"# Wildfire Calendar export | area: {name} | country: {country} | "
            f"bbox: {tuple(round(b, 3) for b in bbox)}\n"
            f"# units: VIIRS-equivalent {unit} | sources: NASA FIRMS MODIS C6.1, VIIRS S-NPP 375m\n"
            f"# harmonization: monthly VIIRS/MODIS factor, held-out error {val['err']:.0f}%, trust {level}\n")

    def csv(frame):
        b = io.StringIO()
        b.write(head)
        frame.to_csv(b)
        return b.getvalue().encode()

    d1, d2, d3 = st.columns(3)
    with d1:
        st.markdown(U.readout("Calendar", "year × month", f"{len(mon)} rows"), unsafe_allow_html=True)
        st.download_button("Download CSV", csv(mon.rename(columns=dict(enumerate(S.MONTHS, 1)))),
                           "calendar_monthly.csv", "text/csv", key="d1")
    with d2:
        st.markdown(U.readout("Daily series", "MODIS · VIIRS · harmonized", f"{len(dly):,} days"),
                    unsafe_allow_html=True)
        st.download_button("Download CSV", csv(dly.assign(harmonized=act)), "daily_series.csv", "text/csv", key="d2")
    with d3:
        st.markdown(U.readout("Hotspots", "every detection", f"{len(df):,} rows"), unsafe_allow_html=True)
        st.download_button("Download CSV", csv(df), "hotspots.csv", "text/csv", key="d3")

# ---------------- method ----------------
with tabs[5]:
    st.markdown("""
**The problem.** MODIS (since 2000, 1 km pixels) and VIIRS (since 2012, 375 m) see fire differently. A plain count
jumps up in 2012, and any 25-year trend becomes meaningless.

**What we do**
1. Keep confident vegetation-fire detections: MODIS confidence ≥ 30, VIIRS nominal or high, no volcanoes or static sources.
2. Count **active 0.1° cells per day**. This changes less with pixel size than raw detection counts.
3. For the selected area, learn a **VIIRS / MODIS factor for each month** from 2013–2025. When a month has little fire, the factor is pulled toward the all-year value.
4. Before July 2002 only Terra flew, so Terra-only days get a Terra → Terra+Aqua factor learned from 2003–2011.
5. Days when VIIRS saw nothing in the whole country while MODIS did are treated as **outages** and filled from MODIS.
6. **Test**: predict every 2013–2025 year from MODIS alone, without that year. The error sets the trust label.

Data: NASA FIRMS (MODIS C6.1 MCD14ML, VIIRS S-NPP VNP14IMGTDL).
""")

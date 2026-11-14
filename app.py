"""Wildfire Calendar: one 25-year fire record from MODIS + VIIRS for any area you draw.

    streamlit run app.py
"""
from __future__ import annotations

import io
import math

import folium
import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
from folium.plugins import Draw
from streamlit_folium import st_folium

import data
import harmonize as H
import seasons as S

st.set_page_config(page_title="Wildfire Calendar", page_icon="🔥", layout="wide")

PRESETS = {
    "Kazakhstan": {
        "Kostanay region (steppe)": (60.0, 48.5, 66.5, 54.5),
        "Naurzum reserve (steppe & pine islands)": (63.5, 51.0, 65.5, 52.0),
        "Arakaragai pine forest": (63.5, 52.0, 64.5, 53.0),
    },
    "Argentina": {
        "Paraná Delta (wetlands)": (-60.9, -34.3, -58.3, -32.0),
        "Corrientes & Iberá (wetlands, grassland)": (-59.7, -30.8, -55.6, -27.2),
        "Córdoba hills (shrubland)": (-65.5, -32.5, -64.0, -30.0),
        "Comarca Andina, Chubut (Andean forest)": (-71.8, -42.3, -71.2, -41.8),
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
TRUST_ICON = {"High": "🟢", "Medium": "🟡", "Low": "🔴", "Insufficient": "⚪"}
SCALES = {"Colour-blind safe (cividis)": "cividis", "Fire (yellow → red)": "YlOrRd"}

# ---------------- sidebar ----------------
countries = data.countries()
if not countries:
    st.error("No data yet. Run `python fetch.py Kazakhstan` and `python data.py Kazakhstan` first.")
    st.stop()
with st.sidebar:
    st.header("🔥 Wildfire Calendar")
    country = st.selectbox("Country", countries)
    meta = data.meta(country)
    mode = st.radio("Area", ["Example area", "Draw on map", "Point + radius"], horizontal=False)
    ring = None
    if mode == "Example area":
        presets = PRESETS.get(country, {}) or {"Whole country": tuple(meta["bbox"])}
        name = st.selectbox("Example area", list(presets))
        bbox = presets[name]
    elif mode == "Point + radius":
        c1, c2 = st.columns(2)
        b0 = meta["bbox"]
        lat = c1.number_input("Latitude", -90.0, 90.0, round((b0[1] + b0[3]) / 2, 2), format="%.3f")
        lon = c2.number_input("Longitude", -180.0, 180.0, round((b0[0] + b0[2]) / 2, 2), format="%.3f")
        km = st.slider("Radius, km", 5, 300, 50)
        dlat, dlon = km / 111.0, km / (111.0 * max(math.cos(math.radians(lat)), 0.05))
        bbox = (lon - dlon, lat - dlat, lon + dlon, lat + dlat)
        ring = [(lon + dlon * math.cos(a), lat + dlat * math.sin(a)) for a in np.linspace(0, 2 * math.pi, 64)]
        name = f"{km} km around {lat:.2f}, {lon:.2f}"
    else:
        ring = st.session_state.get(f"ring_{country}")
        if ring:
            xs, ys = [p[0] for p in ring], [p[1] for p in ring]
            bbox = (min(xs), min(ys), max(xs), max(ys))
            name = "Drawn area"
        else:
            bbox = tuple(meta["bbox"])
            name = None
            st.info("Draw a rectangle or polygon on the map (toolbar at its top-left).")
    measure = st.selectbox("Activity measure", list(H.MEASURES), format_func=H.MEASURES.get,
                           help="Active 0.1° cells per day is the most stable across sensors (default).")
    scale = SCALES[st.selectbox("Colours", list(SCALES))]
    years = st.slider("Years shown", 2000, int(meta["end"][:4]), (2000, int(meta["end"][:4])))
    st.caption(f"Data: NASA FIRMS MODIS C6.1 + VIIRS S-NPP 375 m, {meta['start']} – {meta['end']}. "
               f"{len(meta['viirs_gaps'])} VIIRS outage days filled from MODIS.")

# ---------------- map ----------------
st.title("Wildfire Calendar")
st.caption("When does land burn here, and is this year normal? One 25-year record from two NASA satellite sensors.")
with st.expander("🗺️ Area of interest", expanded=(mode == "Draw on map")):
    w, s_, e, n = bbox
    fm = folium.Map(location=[(s_ + n) / 2, (w + e) / 2], tiles="CartoDB positron", zoom_start=6)
    if name:
        if ring:
            folium.Polygon([(y, x) for x, y in ring], color="#d7301f", fill=True, fill_opacity=0.1).add_to(fm)
        else:
            folium.Rectangle([(s_, w), (n, e)], color="#d7301f", fill=True, fill_opacity=0.1).add_to(fm)
    fm.fit_bounds([(s_, w), (n, e)])
    Draw(draw_options={"polyline": False, "circle": False, "marker": False, "circlemarker": False,
                       "polygon": True, "rectangle": True}, edit_options={"edit": False}).add_to(fm)
    out = st_folium(fm, height=380, use_container_width=True, returned_objects=["last_active_drawing"],
                    key=f"map_{country}")
    drawing = (out or {}).get("last_active_drawing")
    if drawing and drawing.get("geometry", {}).get("type") == "Polygon":
        new = [tuple(p) for p in drawing["geometry"]["coordinates"][0]]
        if new != st.session_state.get(f"ring_{country}"):
            st.session_state[f"ring_{country}"] = new
            if mode == "Draw on map":
                st.rerun()
            else:
                st.info("Area drawn — switch the sidebar to **Draw on map** to analyse it.")
if not name:
    st.stop()


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
    act = H.harmonized(dly, f)
    val = H.validate(dly)
    return df, dly, f, act, val


ring_key = tuple(map(tuple, ring)) if ring else None
df, dly, fit, act, val = analyse(country, tuple(bbox), ring_key, measure)
if df.empty or act.sum() == 0:
    st.warning("No fire detections in this area. Try a larger one.")
    st.stop()
level, why = H.trust(val, measure)
mon = S.monthly(act)
wk = S.weekly(act)
last_year = int(act.index.max().year)
clim = S.climatology(wk, exclude=last_year)
seas = S.fire_seasons(clim)
lm = S.latest_month(act, mon)
unit = H.MEASURES[measure].lower()

st.subheader(name + f" · {country}")
st.caption(f"{int(df.good.sum()):,} confident hotspots · {meta['start']} – {meta['end']} · "
           f"units: VIIRS-equivalent {unit}")
k1, k2, k3, k4 = st.columns(4)
k1.metric("Can old and new years be compared?", f"{TRUST_ICON[level]} {level}",
          help=why + " Tested by predicting each 2013–2025 year from MODIS alone, without using that year.")
k1.caption(why)
if seas:
    k2.metric("Main fire season", S.season_label(seas[0]), f"{seas[0]['share']:.0f}% of the year's fire",
              delta_color="off")
    if len(seas) > 1:
        k2.caption("Also: " + "; ".join(f"{S.season_label(x)} ({x['share']:.0f}%)" for x in seas[1:3]))
if lm:
    ratio = lm["ratio"]
    word = ("far above" if ratio > 2 else "above" if ratio > 1.25 else "below" if ratio < 0.8 else "near")
    k3.metric(f"{S.MONTHS[lm['month'] - 1]} {lm['year']} vs usual",
              f"{ratio:.1f}× median" if np.isfinite(ratio) else "no fire usually",
              f"{word} normal · rank {lm['rank']} of {lm['n']}", delta_color="off")
yr = S.yearly(act)
if len(yr):
    top = yr.activity.idxmax()
    k4.metric("Most active year", int(top), f"{yr.activity.max() / yr.activity.median():.1f}× a typical year",
              delta_color="off")

tabs = st.tabs(["📅 Calendar", "📈 This year vs normal", "🔍 Seasons & anomalies", "🛰️ Harmonization",
                "⬇️ Download", "ℹ️ Method"])

# ---------------- calendar ----------------
with tabs[0]:
    view = st.radio("Resolution", ["Months", "Weeks"], horizontal=True, label_visibility="collapsed")
    if view == "Months":
        t = mon.loc[years[0]:years[1]]
        z, xs = t.to_numpy(), S.MONTHS
    else:
        t = wk.loc[years[0]:years[1]].reindex(columns=range(1, 53))
        z, xs = t.to_numpy(), [S.week_label(i) for i in t.columns]
    zl = np.log10(np.where(np.isnan(z), np.nan, z) + 1)
    hover = np.vectorize(lambda v: "no data" if np.isnan(v) else f"{v:,.0f}")(z)
    fig = go.Figure(go.Heatmap(z=zl, x=xs, y=t.index.astype(str), colorscale=scale, text=hover,
                               hovertemplate="%{y} %{x}: %{text}<extra></extra>",
                               colorbar=dict(title=unit, tickvals=[0, 1, 2, 3, 4, 5],
                                             ticktext=["0", "10", "100", "1k", "10k", "100k"])))
    fig.update_layout(height=max(380, 22 * len(t)), margin=dict(t=10, l=10, r=10),
                      yaxis=dict(autorange="reversed", dtick=1, title=None), xaxis=dict(side="top", title=None))
    st.plotly_chart(fig, use_container_width=True)
    st.caption("Log colour scale. 2000–2011 = MODIS × learned factor; 2012 onward = VIIRS. "
               "Grey cells: month not fully observed.")

# ---------------- this year ----------------
with tabs[1]:
    y = last_year if last_year in wk.index else wk.index.max()
    cur = wk.loc[y].reindex(range(1, 53))
    xl = [S.week_label(i) for i in range(1, 53)]
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=xl, y=clim.p90.reindex(range(1, 53)), line=dict(width=0), showlegend=False,
                             hoverinfo="skip"))
    fig.add_trace(go.Scatter(x=xl, y=clim.p10.reindex(range(1, 53)), fill="tonexty", line=dict(width=0),
                             fillcolor="rgba(120,120,120,0.25)", name="usual range (10–90%)"))
    fig.add_trace(go.Scatter(x=xl, y=clim["median"].reindex(range(1, 53)), line=dict(color="#555", dash="dot"),
                             name="median year"))
    fig.add_trace(go.Bar(x=xl, y=cur, name=str(y), marker_color="#d7301f"))
    fig.update_layout(height=420, margin=dict(t=10), yaxis_title=f"{unit} per week",
                      legend=dict(orientation="h", y=1.08))
    st.plotly_chart(fig, use_container_width=True)
    if lm:
        st.markdown(f"**{S.MONTHS[lm['month'] - 1]} {lm['year']}**: {lm['value']:,.0f} vs a median of "
                    f"{lm['median']:,.0f} (usual range {lm['p10']:,.0f}–{lm['p90']:,.0f}); "
                    f"rank {lm['rank']} of {lm['n']} years.")
    st.caption(f"Normal is computed from all complete years except {y}.")

# ---------------- seasons & anomalies ----------------
with tabs[2]:
    st.markdown("**Fire seasons** (weeks above the average week)")
    if seas:
        st.dataframe(pd.DataFrame([{"season": S.season_label(x), "peak week": S.week_label(x["peak"]),
                                    "share of yearly fire": f"{x['share']:.0f}%"} for x in seas]),
                     hide_index=True)
    clim_cache = {}

    def clim_wo(yy):
        if yy not in clim_cache:
            clim_cache[yy] = S.climatology(wk, exclude=yy)
        return clim_cache[yy]

    an = S.anomalies(wk, clim_wo)
    st.markdown("**Weeks far above normal for their time of year**")
    if an.empty:
        st.info("No strong anomalies.")
    else:
        st.dataframe(an.head(20).drop(columns=["year", "week"]).round(1), hide_index=True)
    ev = [x for x in EVENTS if x[3] == country and bbox[0] <= x[2] <= bbox[2] and bbox[1] <= x[1] <= bbox[3]]
    st.markdown("**Does the record see fires reported in the news?**")
    if ev:
        v = df[(df.sensor == "VIIRS") & df.good]
        rows = []
        for ds_, la, lo, _, label in ev:
            t0 = pd.Timestamp(ds_)
            counts = {yy: int(v.date.between(t0.replace(year=yy) - pd.Timedelta(days=3),
                                             t0.replace(year=yy) + pd.Timedelta(days=3)).sum())
                      for yy in range(2013, 2026)}
            me = counts[t0.year]
            rank = 1 + sum(c > me for yy, c in counts.items() if yy != t0.year)
            rows.append({"reported fire": label, "hotspots ±3 days": me,
                         "same dates, typical year": int(np.median([c for yy, c in counts.items() if yy != t0.year])),
                         "result": "✅ highest of 2013–2025" if rank == 1 and me else f"rank {rank} of 13"})
        st.dataframe(pd.DataFrame(rows), hide_index=True)
    else:
        st.caption("No documented fire inside this area.")

# ---------------- harmonization ----------------
with tabs[3]:
    c1, c2, c3 = st.columns(3)
    c1.metric("Error, monthly factor (used)", f"{val['err']:.0f}%")
    c2.metric("Error, one factor for all months", f"{val['err_one_k']:.0f}%")
    c3.metric("Error, raw MODIS (no conversion)", f"{val['err_raw']:.0f}%")
    st.caption("Leave-one-year-out test: for each year 2013–2025 the factor is learned from the other years only, "
               "then that year's monthly VIIRS totals are predicted from MODIS. Error = Σ|predicted − actual| / Σ actual.")
    kk = pd.DataFrame({"month": S.MONTHS, "VIIRS / MODIS factor": fit.k.values})
    fig = px.bar(kk, x="month", y="VIIRS / MODIS factor", color_discrete_sequence=["#fc8d59"])
    fig.add_hline(y=fit.k_global, line_dash="dot", annotation_text=f"all-year {fit.k_global:.2f}")
    fig.update_layout(height=300, margin=dict(t=10))
    st.plotly_chart(fig, use_container_width=True)
    o = dly[(dly.index.year >= 2013)].copy()
    o["MODIS × factor"] = o.modis * fit.k.reindex(o.index.month).to_numpy()
    om = o.resample("MS")[["viirs", "MODIS × factor", "modis"]].sum().rename(columns={"viirs": "VIIRS",
                                                                                      "modis": "MODIS raw"})
    fig = px.line(om, labels={"value": f"{unit} per month", "index": "", "variable": ""})
    fig.update_layout(height=320, margin=dict(t=10), legend=dict(orientation="h", y=1.1))
    st.plotly_chart(fig, use_container_width=True)
    if len(val["per_year"]):
        st.dataframe(val["per_year"].round(0).astype(int), use_container_width=False)

# ---------------- download ----------------
with tabs[4]:
    head = (f"# Wildfire Calendar export | area: {name} | country: {country} | bbox: {tuple(round(b, 3) for b in bbox)}\n"
            f"# units: VIIRS-equivalent {unit} | sources: NASA FIRMS MODIS C6.1, VIIRS S-NPP 375m\n"
            f"# harmonization: monthly VIIRS/MODIS factor, held-out error {val['err']:.0f}%, trust {level}\n")

    def csv(frame):
        b = io.StringIO()
        b.write(head)
        frame.to_csv(b)
        return b.getvalue().encode()

    st.download_button("Monthly calendar (year × month)", csv(mon.rename(columns=dict(enumerate(S.MONTHS, 1)))),
                       "calendar_monthly.csv", "text/csv")
    st.download_button("Daily series (MODIS, VIIRS, harmonized)", csv(dly.assign(harmonized=act)),
                       "daily_series.csv", "text/csv")
    st.download_button("Hotspots in this area", csv(df), "hotspots.csv", "text/csv")

# ---------------- method ----------------
with tabs[5]:
    st.markdown("""
**Problem.** MODIS (since 2000, 1 km pixels) and VIIRS (since 2012, 375 m) see fire differently, so a simple
count jumps up in 2012 and long-term trends become meaningless.

**What we do**
1. Keep confident vegetation-fire detections (MODIS confidence ≥ 30, VIIRS nominal/high, no volcano/static sources).
2. Count **active 0.1° cells per day** (default) — less sensitive to pixel size than raw detection counts.
3. For the selected area, learn a **VIIRS / MODIS factor for each month** from 2013–2025, pulled toward the
   all-year factor when a month has little fire.
4. Before July 2002 only Terra flew; we scale Terra-only days with a Terra → Terra+Aqua factor from 2003–2011.
5. Days when VIIRS saw nothing in the whole country while MODIS did are treated as **outages** and filled from MODIS.
6. **Test it**: predict every 2013–2025 year from MODIS alone, without that year → error → trust label.
""")

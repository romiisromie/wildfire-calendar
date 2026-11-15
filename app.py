"""Wildfire Calendar: one 25-year fire record from MODIS + VIIRS for any area you draw.

    streamlit run app.py
"""
from __future__ import annotations

import io
import math
import re
import subprocess
import sys
from pathlib import Path

import folium
import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from folium.plugins import Draw, HeatMap
from streamlit_folium import st_folium

import climate as C
import data
import fetch
import harmonize as H
import i18n
from i18n import t as T
import nrt
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
METHOD = {
    "en": """
**Why now.** MODIS on Terra and Aqua is near the end of its life. Its 25-year fire record continues only through VIIRS, and only if the two are put on one scale.

**The problem.** MODIS (since 2000, 1 km pixels) and VIIRS (since 2012, 375 m) see fire differently. A plain count
jumps up in 2012, and any 25-year trend becomes meaningless.

**What we do**
1. Keep confident vegetation-fire detections: MODIS confidence ≥ 30, VIIRS nominal or high, no volcanoes or static sources.
2. Count **active 0.1° cells per day**. This changes less with pixel size than raw detection counts.
3. For the selected area, learn a **VIIRS / MODIS factor for each month** from 2013–2025. When a month has little fire, the factor is pulled toward the all-year value.
4. Before July 2002 only Terra flew, so Terra-only days get a Terra → Terra+Aqua factor learned from 2003–2011.
5. Days when VIIRS saw nothing in the whole country while MODIS did are treated as **outages** and filled from MODIS.
6. **Test**: predict every 2013–2025 year from MODIS alone, without that year. The error sets the trust label.

Data: NASA FIRMS (MODIS C6.1 MCD14ML, VIIRS S-NPP VNP14IMGTDL; last 7 days: VIIRS NOAA-20 NRT, compared with an S-NPP normal: same instrument design, not cross-calibrated) and NASA POWER daily weather.
**Use of AI.** The code of this app was written with an AI coding assistant (Claude Code, Anthropic), directed and checked by the team. No images, audio or data were AI-generated: all numbers come from NASA data.
""",
    "es": """
**Por qué ahora.** MODIS en Terra y Aqua llega al final de su vida útil. Su registro de 25 años solo continúa con VIIRS, y solo si ambos están en la misma escala.

**El problema.** MODIS (desde 2000, píxeles de 1 km) y VIIRS (desde 2012, 375 m) ven el fuego de forma distinta. Un conteo
simple salta en 2012 y cualquier tendencia de 25 años pierde sentido.

**Qué hacemos**
1. Conservamos detecciones confiables de incendios de vegetación: confianza MODIS ≥ 30, VIIRS nominal o alta, sin volcanes ni fuentes fijas.
2. Contamos **celdas activas de 0,1° por día**, que dependen menos del tamaño del píxel que el número de detecciones.
3. Para el área elegida aprendemos un **factor VIIRS / MODIS por mes** con 2013–2025. Si un mes tiene poco fuego, el factor se acerca al valor anual.
4. Antes de julio de 2002 solo volaba Terra: esos días se ajustan con un factor Terra → Terra+Aqua aprendido en 2003–2011.
5. Los días en que VIIRS no vio nada en todo el país pero MODIS sí se tratan como **cortes** y se completan con MODIS.
6. **Prueba**: predecimos cada año 2013–2025 solo con MODIS, sin usar ese año. El error define la etiqueta de confianza.

Datos: NASA FIRMS (MODIS C6.1, VIIRS S-NPP; últimos 7 días: VIIRS NOAA-20 NRT, comparado con una normal de S-NPP: mismo diseño de instrumento, sin calibración cruzada) y clima diario NASA POWER.
**Uso de IA.** El código de esta aplicación se escribió con un asistente de programación con IA (Claude Code, Anthropic), dirigido y revisado por el equipo. No se generaron con IA imágenes, audio ni datos: todas las cifras provienen de datos de la NASA.
""",
    "ru": """
**Почему сейчас.** MODIS на Terra и Aqua доживает срок службы. Его 25-летний ряд пожаров продолжится только через VIIRS — и только если привести их к одной шкале.

**Проблема.** MODIS (с 2000 года, пиксель 1 км) и VIIRS (с 2012 года, 375 м) видят огонь по-разному. Простой подсчёт
подскакивает в 2012 году, и любой 25-летний тренд теряет смысл.

**Что мы делаем**
1. Оставляем надёжные детекции пожаров растительности: уверенность MODIS ≥ 30, VIIRS nominal/high, без вулканов и промышленных источников.
2. Считаем **активные ячейки 0,1° в день** — они меньше зависят от размера пикселя, чем число точек.
3. Для выбранной области обучаем **коэффициент VIIRS / MODIS для каждого месяца** на 2013–2025. Если в месяце мало огня, коэффициент тянется к годовому.
4. До июля 2002 года летал только Terra: такие дни домножаются на коэффициент Terra → Terra+Aqua, обученный на 2003–2011.
5. Дни, когда VIIRS ничего не увидел во всей стране, а MODIS увидел, считаются **сбоями** и заполняются из MODIS.
6. **Проверка**: каждый год 2013–2025 предсказываем только по MODIS, не используя этот год. Ошибка задаёт уровень доверия.

Данные: NASA FIRMS (MODIS C6.1, VIIRS S-NPP; последние 7 дней: VIIRS NOAA-20 NRT в сравнении с нормой по S-NPP: прибор того же устройства, без взаимной калибровки) и суточная погода NASA POWER.
**Использование ИИ.** Код приложения написан с помощью ИИ-ассистента для программирования (Claude Code, Anthropic) под руководством и с проверкой команды. Изображения, звук и данные ИИ не генерировал: все цифры взяты из данных NASA.
""",
}
CHART_CFG = {"displaylogo": False, "modeBarButtons": [["toImage"]],
             "toImageButtonOptions": {"format": "png", "scale": 2, "filename": "wildfire-calendar"}}
SCALES = {"Burn (dark → bright)": U.BURN, "Cividis": "cividis"}

countries = data.countries()
if not countries:
    st.error("No data yet. Run `python fetch.py Kazakhstan` and `python data.py Kazakhstan` first.")
    st.stop()

# ---------------- header ----------------
qp_lang = st.query_params.get("lang", "EN").upper()
hb, hl = st.columns([6, 1], vertical_alignment="bottom")
lang_key = hl.segmented_control("Language", list(i18n.LANGS), default=qp_lang if qp_lang in i18n.LANGS else "EN",
                                label_visibility="collapsed", key="lang") or "EN"
i18n.lang = i18n.LANGS[lang_key]
st.query_params["lang"] = lang_key
hb.markdown(U.brand(T("When does this land burn, and is this year normal?")), unsafe_allow_html=True)
st.markdown(U.orbit(), unsafe_allow_html=True)

# ---------------- settings (rarely changed) ----------------
with st.sidebar:
    st.markdown(U.section("⚙", T("Settings")), unsafe_allow_html=True)
    measure = st.selectbox(T("Activity measure"), list(H.MEASURES), format_func=lambda k: T(H.MEASURES[k]),
                           help="Active 0.1° cells per day changes least between the two sensors (default).")
    scale_name = st.radio(T("Calendar colours"), list(SCALES),
                          help="Both scales get brighter with more fire, so they read in greyscale and for colour-blind users.")
    scale = SCALES[scale_name]
    st.markdown(U.section("+", T("Add a country")), unsafe_allow_html=True)
    LOGS = Path(__file__).parent / "data" / "logs"
    HOSTED = Path("/mount/src").exists()  # Streamlit Community Cloud: ~1 GB RAM, temporary disk
    if HOSTED:
        st.markdown('<div class="wc-note">' + T("The online demo ships Kazakhstan and Argentina. To add any other "
                    "country, run the app locally: python fetch.py Brazil --build") + '</div>', unsafe_allow_html=True)
    with st.form("add_country", border=False) if not HOSTED else st.empty():
        if not HOSTED:
            want = st.text_input(T("Country name as in NASA FIRMS"), placeholder="e.g. Brazil, United States, Mongolia")
            go_ = st.form_submit_button(T("Download 2000–2025"))
        else:
            want, go_ = "", False
    if go_ and want.strip():
        cname = "_".join(w[:1].upper() + w[1:] for w in want.strip().replace("_", " ").split())
        if not re.fullmatch(r"[A-Z][A-Za-z_'-]{1,60}", cname):
            st.error(T("Use letters only, e.g. United States."))
        elif cname in countries:
            st.info(f"{cname} is already loaded.")
        elif not fetch.exists(cname):
            st.error(f"FIRMS has no archive called “{cname}”. Use the English name, e.g. United_States.")
        else:
            LOGS.mkdir(parents=True, exist_ok=True)
            log = open(LOGS / f"{cname}.log", "w")
            subprocess.Popen([sys.executable, str(Path(__file__).parent / "fetch.py"), cname, "--build"],
                             stdout=log, stderr=subprocess.STDOUT, cwd=Path(__file__).parent)
            st.success(f"Started {cname}. Large countries take a while; this page updates by itself.")

    @st.fragment(run_every=5)
    def progress():
        for f in sorted(LOGS.glob("*.log")) if LOGS.exists() else []:
            lines = f.read_text(errors="ignore").splitlines()
            if any(l.startswith("BUILT") for l in lines):
                if f.stem not in data.countries():
                    continue
                f.unlink()
                st.rerun(scope="app")
            done = [l for l in lines if l.startswith("[")]
            n = int(done[-1][1:].split("/")[1].split("]")[0]) if done else 40
            st.progress(len(done) / n, text=f"{f.stem}: {len(done)}/{n} files"
                        + (" · building…" if any(l.startswith("DONE") for l in lines) else ""))
            if any("Traceback" in l for l in lines):
                st.error(f"{f.stem}: failed — see data/logs/{f.name}")

    progress()

# ---------------- area picker ----------------
c1, c2, c3 = st.columns([1.1, 1.6, 3.3], vertical_alignment="bottom")
country = c1.selectbox(T("Country"), countries)
meta = data.meta(country)
mode = c2.segmented_control(T("Choose area"), ["Example", "Draw", "Point"], default="Example", format_func=T,
                            help=T("Example: ready-made areas · Draw: rectangle or polygon on the map · "
                                   "Point: coordinates and a radius")) or "Example"
ring, name = None, None
if mode == "Example":
    presets = PRESETS.get(country) or {T("Whole country"): tuple(meta["bbox"])}
    name = c3.pills("Area", list(presets), default=list(presets)[0], label_visibility="hidden") or list(presets)[0]
    bbox = presets[name]
elif mode == "Point":
    b0 = meta["bbox"]
    p1, p2, p3 = c3.columns(3)
    lat = p1.number_input(T("Latitude"), -90.0, 90.0, round((b0[1] + b0[3]) / 2, 2), format="%.3f")
    lon = p2.number_input(T("Longitude"), -180.0, 180.0, round((b0[0] + b0[2]) / 2, 2), format="%.3f")
    km = p3.number_input(T("Radius, km"), 5, 500, 50, step=5)
    dlat, dlon = km / 111.0, km / (111.0 * max(math.cos(math.radians(lat)), 0.05))
    bbox = (lon - dlon, lat - dlat, lon + dlon, lat + dlat)
    ring = [(lon + dlon * math.cos(a), lat + dlat * math.sin(a)) for a in np.linspace(0, 2 * math.pi, 64)]
    name = T("{km} km around {lat}°, {lon}°", km=km, lat=f"{lat:.2f}", lon=f"{lon:.2f}")
else:
    ring = st.session_state.get(f"ring_{country}")
    if ring:
        xs, ys = [p[0] for p in ring], [p[1] for p in ring]
        bbox = (min(xs), min(ys), max(xs), max(ys))
        name = T("Your drawn area")
        if c3.button(T("Clear drawing")):
            st.session_state.pop(f"ring_{country}")
            st.rerun()
    else:
        bbox = tuple(meta["bbox"])
        c3.markdown('<div class="wc-note">' + T("Use the ▭ or ⬠ tool on the map’s left edge to outline an area.") + '</div>',
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


@st.cache_data(show_spinner=False, max_entries=32)
def last_week(bbox, ring, measure, stamp):
    d, when, end = nrt.last7(bbox)
    if ring and len(d):
        d = d[data.inside(d.lon.to_numpy(), d.lat.to_numpy(), list(ring))]
    return d.reset_index(drop=True), when, end


@st.cache_data(show_spinner="Getting NASA POWER weather…", max_entries=16)
def get_weather(lat, lon):
    return C.weather(lat, lon)


def recent_vs_normal(d7, act, measure, end):
    """Activity in the last 7 days (NOAA-20 VIIRS) against the same calendar days in 2013–2025 (S-NPP VIIRS)."""
    days = pd.date_range(end - pd.Timedelta(days=6), end)
    x = d7.assign(sensor="VIIRS", sat="N", good=True, type=0)
    now = H.daily(x, days[0], days[-1], measure).viirs.sum() if len(x) else 0.0
    past = []
    for y in range(2013, int(act.index.max().year) + 1):
        try:
            win = act.loc[days[0].replace(year=y):days[-1].replace(year=y)]
        except ValueError:
            continue
        if len(win) == 7:
            past.append(win.sum())
    if len(past) < 5:
        return None
    past = np.array(past)
    return {"now": float(now), "median": float(np.median(past)), "p90": float(np.quantile(past, .9)),
            "rank": int(1 + (past > now).sum()), "n": len(past) + 1, "start": days[0], "end": days[-1]}


res = None
if name:
    ring_key = tuple(map(tuple, ring)) if ring else None
    res = analyse(country, tuple(bbox), ring_key, measure)
    if res[0].empty or res[3].sum() == 0:
        res = None
        st.warning(T("No fire detections in this area. Try a larger one."))

d7, d7_when, d7_end = (None, None, None)
if res is not None:
    try:
        stamp = nrt.stamp(tuple(bbox))
        if stamp is not None:
            d7, d7_when, d7_end = last_week(tuple(bbox), tuple(map(tuple, ring)) if ring else None, measure, stamp)
    except Exception:  # NRT is a bonus: never break the page over it
        d7 = None

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
    if d7 is not None and len(d7):
        for _, r in d7.sample(min(len(d7), 400), random_state=1).iterrows():
            folium.CircleMarker((r.lat, r.lon), radius=3, color="#fff1b8", weight=1, fill=True, fill_color=U.FLAME,
                                fill_opacity=0.9, tooltip=f"{r.date:%d %b}: {r.frp:.0f} MW").add_to(fm)
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
        st.info(T("Area drawn. Switch **Choose area** to **Draw** to analyse it."))
    if res is not None:
        st.markdown('<div class="wc-note">' + T("Glow = VIIRS hotspots of the last three years · bright dots = fires of "
                    "the last 7 days (NOAA-20) · dashed line = analysed area.") + '</div>', unsafe_allow_html=True)

if res is None:
    with right:
        st.markdown('<div class="wc-kicker">' + T("No area yet") + '</div><div class="wc-area">'
                    + T("Outline a place on the map") + '</div><div class="wc-lede">'
                    + T("Pick an example, draw a shape, or enter coordinates.") + '</div>', unsafe_allow_html=True)
    st.stop()

df, dly, fit, act, val = res
level, why_t = H.trust(val, measure)
why = T(why_t, e=f"{val['err']:.0f}")
mon = S.monthly(act)
wk = S.weekly(act)
last_year = int(act.index.max().year)
clim = S.climatology(wk, exclude=last_year)
seas = S.fire_seasons(clim)
lm = S.latest_month(act, mon)
yr = S.yearly(act)
unit = T(H.MEASURES[measure]).lower()
MON = i18n.month_names()
L = i18n.months

with right:
    st.markdown(f'<div class="wc-kicker">{U.esc(country)} · {meta["start"][:4]}–{meta["end"][:4]}</div>'
                f'<div class="wc-area">{U.esc(name)}</div>', unsafe_allow_html=True)
    lede = []
    if seas:
        lede.append(T("Land here burns mostly <em>{s}</em> ({p}% of a year’s fire)", s=L(S.season_label(seas[0])),
                      p=f"{seas[0]['share']:.0f}")
                    + (T(", with a second season <em>{s}</em>", s=L(S.season_label(seas[1]))) if len(seas) > 1 else "")
                    + ".")
    if lm and np.isfinite(lm["ratio"]):
        r = lm["ratio"]
        word = "far more than" if r > 2 else "more than" if r > 1.25 else "less than" if r < 0.8 else "about as much as"
        lede.append(T("{m} burned <em>{w} usual</em> ({r}× the median).", m=f"{MON[lm['month'] - 1].capitalize()} {lm['year']}",
                      w=T(word), r=f"{r:.1f}"))
    if len(yr) >= 10:
        a, b = yr.activity.loc[:2010].mean(), yr.activity.loc[2016:].mean()
        if a > 0 and level in ("High", "Medium"):
            ch = 100 * (b / a - 1)
            lede.append(T("Since the 2000s, yearly fire is <em>{d} {p}%</em>.", d=T("down" if ch < 0 else "up"),
                          p=f"{abs(ch):.0f}"))
    st.markdown(f'<div class="wc-lede">{" ".join(lede)}</div>', unsafe_allow_html=True)

    rv = recent_vs_normal(d7, act, measure, d7_end) if d7_end is not None else None
    if rv:
        rr = rv["now"] / rv["median"] if rv["median"] > 0 else np.nan
        val_txt = f"{rv['now']:,.0f}" + (f"  ·  {rr:.1f}×" if np.isfinite(rr) else "")
        st.markdown(U.readout(T("Last 7 days · {a}–{b}", a=f"{rv['start']:%d}", b=L(f"{rv['end']:%d %b}")), val_txt,
                              T("{u} · normal for these days {m} · rank {r} of {n} · updated {t} UTC", u=unit,
                                m=f"{rv['median']:,.0f}", r=rv["rank"], n=rv["n"], t=L(f"{d7_when:%d %b %H:%M}")),
                              dot=U.EMBER if rv["now"] > rv["p90"] else None), unsafe_allow_html=True)
    color, short = TRUST[level]
    st.markdown(U.readout(T("Old vs new years comparable?"), T(level), f"{T(short)} · {why}", dot=color),
                unsafe_allow_html=True)
    if lm:
        mname = f"{MON[lm['month'] - 1]} {lm['year']}"
        if np.isfinite(lm["ratio"]):
            st.markdown(U.readout(T("{m} vs median", m=mname), f"{lm['ratio']:.2f}×",
                                  T("rank {r} of {n} years · usual {a}–{b}", r=lm["rank"], n=lm["n"],
                                    a=f"{lm['p10']:,.0f}", b=f"{lm['p90']:,.0f}")),
                        unsafe_allow_html=True)
        else:
            st.markdown(U.readout(f"{mname}", f"{lm['value']:,.0f}",
                                  T("{u} · this month usually has almost no fire here", u=unit)), unsafe_allow_html=True)
    if len(yr):
        top = int(yr.activity.idxmax())
        st.markdown(U.readout(T("Worst year on record"), str(top),
                              T("{x}× a typical year", x=f"{yr.activity.max() / yr.activity.median():.1f}")),
                    unsafe_allow_html=True)
    st.markdown(U.readout(T("Hotspots analysed"), f"{int(df.good.sum()):,}",
                          f"{(df.sensor == 'MODIS').sum():,} MODIS · {(df.sensor == 'VIIRS').sum():,} VIIRS"),
                unsafe_allow_html=True)

tabs = st.tabs([T(x) for x in ["Calendar", "This year", "Climate & shift", "Seasons & events", "Harmonization",
                                "Compare & download", "Method"]])

# ---------------- calendar ----------------
with tabs[0]:
    a1, a2 = st.columns([1, 3], vertical_alignment="center")
    view = a1.segmented_control("Grid", ["Months", "Weeks"], default="Months", format_func=T,
                                label_visibility="collapsed") or "Months"
    years = a2.slider("Years", int(mon.index.min()), last_year, (int(mon.index.min()), last_year),
                      label_visibility="collapsed")
    if view == "Months":
        t = mon.loc[years[0]:years[1]]
        z, xs = t.to_numpy(), MON
    else:
        t = wk.loc[years[0]:years[1]].reindex(columns=range(1, 53))
        z, xs = t.to_numpy(), [L(S.week_label(i)) for i in t.columns]
    zl = np.log10(z + 1)
    top = max(1.0, float(np.nanmax(zl)))
    tv = [v for v in range(0, 7) if v <= top + 0.01]
    hover = np.vectorize(lambda v: T("not observed") if np.isnan(v) else f"{v:,.0f}")(z)
    fig = go.Figure(go.Heatmap(z=zl, x=xs, y=t.index, colorscale=scale, text=hover, xgap=2, ygap=2,
                               zmin=0, zmax=top, hovertemplate="%{x} %{y}<br><b>%{text}</b> " + unit + "<extra></extra>",
                               colorbar=dict(title=dict(text=unit, side="right"), tickvals=tv, thickness=10,
                                             ticktext=["0" if v == 0 else f"{10 ** v:,.0f}" if v < 3 else f"{10 ** v / 1000:,.0f}k"
                                                       for v in tv], outlinewidth=0)))
    if years[0] <= 2011 < years[1]:
        fig.add_hline(y=2011.5, line=dict(color=U.MUTED, width=1, dash="dot"))
        fig.add_annotation(x=1.0, xref="paper", y=2011.5, text=T("VIIRS starts ↓"), showarrow=False, yshift=-9,
                           xanchor="right", font=dict(size=10, color=U.MUTED))
    fig.update_layout(height=max(380, 24 * len(t) + 60), margin=dict(t=30, l=10, r=10, b=10),
                      yaxis=dict(autorange="reversed", dtick=1, title=None, showgrid=False),
                      xaxis=dict(side="top", title=None, showgrid=False))
    st.plotly_chart(fig, width="stretch", config=CHART_CFG)
    st.markdown('<div class="wc-note">' + T("Brighter = more fire (log scale). Before 2012 values are MODIS converted to "
                "VIIRS units; empty cells were not fully observed.") + '</div>', unsafe_allow_html=True)

# ---------------- this year ----------------
with tabs[1]:
    y = last_year
    cur = wk.loc[y].reindex(range(1, 53)) if y in wk.index else pd.Series(np.nan, index=range(1, 53))
    lo, hi, med = (clim[c].reindex(range(1, 53)) for c in ("p10", "p90", "median"))
    xl = [L(S.week_label(i)) for i in range(1, 53)]
    colors = np.where(cur > hi, U.EMBER, np.where(cur < lo, U.COOL, "#8a5a3c"))
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=xl, y=hi, line=dict(width=0), showlegend=False, hoverinfo="skip"))
    fig.add_trace(go.Scatter(x=xl, y=lo, fill="tonexty", line=dict(width=0), fillcolor="rgba(236,227,212,0.08)",
                             name=T("usual range (10–90%)"), hoverinfo="skip"))
    fig.add_trace(go.Bar(x=xl, y=cur, name=str(y), marker_color=colors, marker_line_width=0,
                         hovertemplate="week of %{x}: %{y:,.0f}<extra></extra>"))
    fig.add_trace(go.Scatter(x=xl, y=med, line=dict(color=U.INK, dash="dot", width=1.2), name=T("median year"),
                             hovertemplate="median: %{y:,.0f}<extra></extra>"))
    fig.update_layout(height=420, margin=dict(t=10, b=10), bargap=0.15, yaxis_title=T("{u} per week", u=unit),
                      xaxis=dict(tickmode="array", tickvals=xl[::4], tickangle=0),
                      legend=dict(orientation="h", y=1.06, x=0))
    st.plotly_chart(fig, width="stretch", config=CHART_CFG)
    st.markdown(f'<div class="wc-note"><span style="color:{U.EMBER}">■</span> {T("above the usual range")} · '
                f'<span style="color:#8a5a3c">■</span> {T("within")} · <span style="color:{U.COOL}">■</span> '
                f'{T("below")}. ' + T("“Usual” = complete years 2000–{y}.", y=y - 1) + '</div>', unsafe_allow_html=True)

# ---------------- climate & season shift ----------------
with tabs[2]:
    big = [x for x in seas if x["share"] >= 10][:2]
    if not big:
        st.markdown('<div class="wc-note">' + T("No clear fire season here to analyse.") + '</div>', unsafe_allow_html=True)
    modis_only = dly.modis * fit.k.reindex(dly.index.month).to_numpy()
    try:
        wx = get_weather(round((bbox[1] + bbox[3]) / 2, 2), round((bbox[0] + bbox[2]) / 2, 2))
    except Exception:
        wx = None
        st.warning(T("NASA POWER weather is unavailable right now; showing season timing only."))
    for i, sz in enumerate(big):
        st.markdown(U.section(f"{i + 1}", T("Season {s} · {p}% of yearly fire", s=L(S.season_label(sz)), p=f"{sz['share']:.0f}")),
                    unsafe_allow_html=True)
        rep = C.shift_report(act, modis_only, sz)
        tm = rep["timing"]
        if len(tm) < 8:
            st.markdown('<div class="wc-note">' + T("Too few complete seasons.") + '</div>', unsafe_allow_html=True)
            continue
        g1, g2 = st.columns([3, 2], gap="large")
        with g1:
            fig = go.Figure()
            for q, col, wdt in (("end", "#8a5a3c", 1), ("middle", U.FLAME, 1.5), ("onset", U.EMBER, 2.5)):
                fig.add_trace(go.Scatter(x=tm.index, y=tm[q], mode="lines+markers", name=T(q), line=dict(color=col, width=wdt),
                                         marker=dict(size=4), customdata=[L(C.doy_label(rep["window_start"], v)) for v in tm[q]],
                                         hovertemplate="%{x}: %{customdata}<extra>" + T(q) + "</extra>"))
                tr = rep[q]
                if np.isfinite(tr["slope"]):
                    xs_ = np.array([tm.index.min(), tm.index.max()])
                    mid = np.median(tm[q]) + tr["slope"] / 10 * (xs_ - np.median(tm.index))
                    fig.add_trace(go.Scatter(x=xs_, y=mid, mode="lines", showlegend=False, hoverinfo="skip",
                                             line=dict(color=col, dash="dot" if not tr["robust"] else "solid", width=1)))
            ticks = np.arange(0, tm[["onset", "end"]].to_numpy().max() + 8, 14)
            fig.update_layout(height=300, margin=dict(t=10, b=10), legend=dict(orientation="h", y=1.1, x=0),
                              yaxis=dict(tickvals=ticks, ticktext=[L(C.doy_label(rep["window_start"], v)) for v in ticks],
                                         autorange="reversed", title=None))
            st.plotly_chart(fig, width="stretch", config=CHART_CFG)
        with g2:
            for q, lab in (("onset", T("Season starts")), ("end", T("Season ends"))):
                tr = rep[q]
                sl = tr["slope"]
                if not np.isfinite(sl):
                    continue
                if abs(sl) < 0.5 or tr["p"] >= .05:
                    v, note = T("no clear shift"), T("{d} days/decade, p = {p}", d=f"{sl:+.1f}", p=f"{tr['p']:.2f}")
                else:
                    v = T("{d} days {w} / decade", d=f"{abs(sl):.1f}", w=T("earlier" if sl < 0 else "later"))
                    note = (f"p = {tr['p']:.3f} · " + T("MODIS alone {d} d/decade", d=f"{tr['modis_slope']:+.1f}")
                            + " · " + T("✔ same on one sensor — not a 2012 artefact" if tr["robust"]
                                        else "⚠ not confirmed by MODIS alone"))
                st.markdown(U.readout(lab, v, note, dot=U.EMBER if tr["robust"] else None), unsafe_allow_html=True)
            if wx is not None:
                fw = C.fire_weather(act, wx, sz)
                if fw:
                    def fmt(c):
                        lo_, hi_ = fw[f"{c}_ci"]
                        return (T("{x}× normal", x=f"{fw[c]:.2f}"),
                                T("90% range {a}–{b} over {n} seasons", a=f"{lo_:.2f}", b=f"{hi_:.2f}", n=fw["years"]))
                    v, nt = fmt("hot")
                    st.markdown(U.readout(T("After hot-dry-windy days"), v, nt, dot=U.EMBER if fw["hot_ci"][0] > 1 else None),
                                unsafe_allow_html=True)
                    v, nt = fmt("calm")
                    st.markdown(U.readout(T("After calm-humid days"), v, nt, dot=U.COOL if fw["calm_ci"][1] < 1 else None),
                                unsafe_allow_html=True)
    st.markdown('<div class="wc-note">' + T("Season timing: the day by which 10% (start), 50% and 90% (end) of a season’s "
                "fire had burned, each year. Trend = Theil–Sen slope, significance = Kendall test. Fire weather: "
                "daily hot-dry-windy index (vapour-pressure deficit × wind, NASA POWER) compared with its normal for the "
                "date; the next 3 days’ fire is compared with the same dates in other years. Coloured dot = the 90% range "
                "excludes 1 (no effect).") + ' ' + T("Many seasons and dates are tested at once, so treat a single "
                "p < 0.05 as a lead to check, not as proof.") + '</div>', unsafe_allow_html=True)
    if wx is not None:
        st.markdown(U.section("↗", T("Fire weather of the last 60 days")), unsafe_allow_html=True)
        rd = C.recent_days(wx)
        cmap = {"hot-dry-windy": U.EMBER, "normal": "#5a4a3e", "calm-humid": U.COOL}
        fig = go.Figure(go.Bar(x=rd.index, y=rd.anom, marker_color=rd.cls.map(cmap), marker_line_width=0,
                               customdata=rd.cls.map(T), hovertemplate="%{x|%d %b}: %{customdata}<extra></extra>"))
        fig.update_layout(height=200, margin=dict(t=10, b=10), yaxis_title=T("vs normal"), bargap=0.1)
        st.plotly_chart(fig, width="stretch", config=CHART_CFG)
        st.markdown('<div class="wc-note">' + T("NASA POWER weather at the area centre, up to {d}.",
                    d=L(f"{wx.index.max():%d %b %Y}")) + '</div>', unsafe_allow_html=True)

# ---------------- seasons & events ----------------
with tabs[3]:
    st.markdown(U.section("A", T("Critical periods (fire seasons)")), unsafe_allow_html=True)
    if seas:
        st.dataframe(pd.DataFrame([{T("season"): L(S.season_label(x)), T("peak week"): L(S.week_label(x["peak"])),
                                    T("share of yearly fire"): f"{x['share']:.0f}%"} for x in seas]),
                     hide_index=True)
    st.markdown(U.section("B", T("Documented fires — does the satellite record see them?")), unsafe_allow_html=True)
    ev = [x for x in EVENTS if x[3] == country and bbox[0] <= x[2] <= bbox[2] and bbox[1] <= x[1] <= bbox[3]
          and (not ring or data.inside(np.array([x[2]]), np.array([x[1]]), list(ring))[0])]
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
            rows.append({T("reported fire"): label, T("hotspots ±3 days"): me,
                         T("same dates, typical year"): int(np.median([c for yy, c in counts.items() if yy != t0.year])),
                         T("result"): T("highest of 2013–2025") if rank == 1 and me else T("rank {r} of 13", r=rank)})
        st.dataframe(pd.DataFrame(rows), hide_index=True)
    else:
        st.markdown('<div class="wc-note">' + T("No documented fire inside this area.") + '</div>', unsafe_allow_html=True)
    st.markdown(U.section("C", T("Weeks far above normal for their time of year")), unsafe_allow_html=True)
    cache = {}
    an = S.anomalies(wk, lambda yy: cache.setdefault(yy, S.climatology(wk, exclude=yy)))
    if an.empty:
        st.markdown('<div class="wc-note">' + T("No strong anomalies.") + '</div>', unsafe_allow_html=True)
    else:
        st.dataframe(an.head(15).drop(columns=["year", "week"]).round(1), hide_index=True)

# ---------------- harmonization ----------------
with tabs[4]:
    st.markdown(U.section("1", T("How wrong is MODIS × factor on years it never saw?")), unsafe_allow_html=True)
    errs = pd.DataFrame({"method": [T("raw MODIS"), T("one factor"), T("monthly factor (used)")],
                         "error": [val["err_raw"], val["err_one_k"], val["err"]]})
    fig = go.Figure(go.Bar(x=errs.error, y=errs.method, orientation="h", text=[f"{e:.0f}%" for e in errs.error],
                           textposition="outside", marker_color=[U.LINE, "#8a5a3c", U.EMBER],
                           hoverinfo="skip"))
    fig.update_layout(height=170, margin=dict(t=0, b=0, l=0, r=40), xaxis=dict(title=T("held-out monthly error, %"),
                      range=[0, max(100, errs.error.max() * 1.15)]), yaxis=dict(title=None))
    st.plotly_chart(fig, width="stretch", config=CHART_CFG)
    st.markdown('<div class="wc-note">' + T("For each year 2013–2025 the factor is learned from the other years only, "
                "then that year’s monthly VIIRS totals are predicted from MODIS. "
                "Error = Σ|predicted − actual| / Σ actual.") + '</div>', unsafe_allow_html=True)
    st.markdown(U.section("2", T("VIIRS sees this many times more than MODIS, by month")), unsafe_allow_html=True)
    fig = go.Figure(go.Bar(x=MON, y=fit.k.values, marker_color=U.FLAME, marker_line_width=0,
                           hovertemplate="%{x}: ×%{y:.2f}<extra></extra>"))
    fig.add_hline(y=fit.k_global, line=dict(color=U.INK, dash="dot", width=1),
                  annotation_text=T("all-year ×{k}", k=f"{fit.k_global:.2f}"), annotation_font_color=U.MUTED)
    fig.update_layout(height=260, margin=dict(t=10, b=10))
    st.plotly_chart(fig, width="stretch", config=CHART_CFG)
    st.markdown(U.section("3", T("Overlap years: VIIRS vs converted MODIS")), unsafe_allow_html=True)
    o = dly[dly.index.year >= 2013].copy()
    o["conv"] = o.modis * fit.k.reindex(o.index.month).to_numpy()
    om = o.resample("MS")[["viirs", "conv", "modis"]].sum()
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=om.index, y=om.modis, name=T("MODIS raw"), line=dict(color="#6b5a4c", width=1)))
    fig.add_trace(go.Scatter(x=om.index, y=om.viirs, name="VIIRS", line=dict(color=U.EMBER, width=2)))
    fig.add_trace(go.Scatter(x=om.index, y=om.conv, name=T("MODIS × factor"), line=dict(color=U.FLAME, width=1.5,
                                                                                         dash="dot")))
    fig.update_layout(height=320, margin=dict(t=10, b=10), yaxis_title=T("{u} per month", u=unit),
                      legend=dict(orientation="h", y=1.08, x=0))
    st.plotly_chart(fig, width="stretch", config=CHART_CFG)

# ---------------- compare a period & download ----------------
with tabs[5]:
    st.markdown(U.section("1", T("Pick a period: how does it compare with every other year?")), unsafe_allow_html=True)
    first, last = act.index.min().date(), act.index.max().date()
    wk7 = act.rolling(7).sum()
    peak_end = wk7.loc[str(last_year - 5):].idxmax()  # default: the strongest week of the last five years
    default = (max(first, (peak_end - pd.Timedelta(days=6)).date()), peak_end.date())
    per = st.date_input(T("Period"), value=default, min_value=first, max_value=last, format="YYYY-MM-DD",
                        key=f"period_{country}_{name}")
    if isinstance(per, (tuple, list)) and len(per) == 2 and (per[1] - per[0]).days <= 365:
        p0, p1 = pd.Timestamp(per[0]), pd.Timestamp(per[1])
        sw = S.same_window(act, p0, p1)
        here = float(act.loc[p0:p1].sum())
        others = sw.drop(index=p0.year, errors="ignore")
        med = float(others.median()) if len(others) else np.nan
        rank = int(1 + (others > here).sum())
        c1, c2, c3 = st.columns(3)
        c1.markdown(U.readout(T("Selected period"), f"{here:,.0f}", unit + f" · {p0:%Y-%m-%d} → {p1:%Y-%m-%d}"),
                    unsafe_allow_html=True)
        c2.markdown(U.readout(T("Same dates, median year"), f"{med:,.0f}" if np.isfinite(med) else "—",
                              T("{x}× the median", x=f"{here / med:.1f}") if med > 0 else ""),
                    unsafe_allow_html=True)
        c3.markdown(U.readout(T("Rank among {n} years", n=len(others) + 1), f"#{rank}",
                              T("1 = most fire on these dates since 2000")), unsafe_allow_html=True)
        cols = [U.EMBER if y == p0.year else ("#8a5a3c" if y < 2012 else "#b07a52") for y in sw.index]
        fig = go.Figure(go.Bar(x=sw.index, y=sw.values, marker_color=cols, marker_line_width=0,
                               hovertemplate="%{x}: %{y:,.0f}<extra></extra>"))
        if np.isfinite(med):
            fig.add_hline(y=med, line=dict(color=U.INK, dash="dot", width=1),
                          annotation_text=T("median"), annotation_font_color=U.MUTED)
        fig.update_layout(height=300, margin=dict(t=10, b=10), yaxis_title=unit, xaxis=dict(dtick=2),
                          bargap=0.2)
        st.plotly_chart(fig, width="stretch", config=CHART_CFG)
        st.markdown('<div class="wc-note">' + T("Same calendar dates in every year of the record, on one harmonized "
                    "scale: lighter bars before 2012 are MODIS converted to VIIRS units.") + '</div>',
                    unsafe_allow_html=True)
        sel = df[(df.date >= p0) & (df.date <= p1)]
    else:
        st.info(T("Choose a start and an end date, at most one year apart."))
        p0, p1, sw, sel = None, None, None, df.iloc[0:0]

    st.markdown(U.section("2", T("Download")), unsafe_allow_html=True)
    head = (f"# Wildfire Calendar export | area: {name} | country: {country} | "
            f"bbox: {tuple(round(b, 3) for b in bbox)}\n"
            f"# units: VIIRS-equivalent {unit} | sources: NASA FIRMS MODIS C6.1, VIIRS S-NPP 375m\n"
            f"# harmonization: monthly VIIRS/MODIS factor, held-out error {val['err']:.0f}%, trust {level}\n")

    def csv(frame):
        b = io.StringIO()
        b.write(head)
        frame.to_csv(b)
        return b.getvalue().encode()

    d1, d2, d3, d4 = st.columns(4)
    with d1:
        st.markdown(U.readout(T("Calendar"), T("year × month"), T("{n} rows", n=len(mon))), unsafe_allow_html=True)
        st.download_button(T("Download CSV"), csv(mon.rename(columns=dict(enumerate(S.MONTHS, 1)))),
                           "calendar_monthly.csv", "text/csv", key="d1")
    with d2:
        st.markdown(U.readout(T("Daily series"), "MODIS · VIIRS · harmonized", T("{n} days", n=f"{len(dly):,}")),
                    unsafe_allow_html=True)
        st.download_button(T("Download CSV"), csv(dly.assign(harmonized=act)), "daily_series.csv", "text/csv", key="d2")
    with d3:
        st.markdown(U.readout(T("Hotspots in the period"), f"{len(sel):,}", T("every detection, both sensors")),
                    unsafe_allow_html=True)
        st.download_button(T("Download CSV"), csv(sel), "hotspots_period.csv", "text/csv", key="d3",
                           disabled=sel.empty)
    with d4:
        st.markdown(U.readout(T("Period vs other years"), T("one row per year"),
                              T("{n} rows", n=0 if sw is None else len(sw))), unsafe_allow_html=True)
        st.download_button(T("Download CSV"), csv(sw.to_frame() if sw is not None else pd.DataFrame()),
                           "period_by_year.csv", "text/csv", key="d4", disabled=sw is None)
    st.markdown('<div class="wc-note">' + T("Every chart has a camera button in its top-right corner to save it as a "
                "PNG.") + '</div>', unsafe_allow_html=True)

# ---------------- method ----------------
with tabs[6]:
    st.markdown(METHOD[i18n.lang])

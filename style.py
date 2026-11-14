"""Look & feel: charcoal ground, ash text, ember accents, telemetry-style numbers."""
from __future__ import annotations

import html

import plotly.graph_objects as go
import plotly.io as pio

INK = "#ece3d4"      # ash
MUTED = "#9a8f82"    # smoke
LINE = "#3a322b"     # burnt edge
PANEL = "#1f1a16"
EMBER = "#ff6a1a"
FLAME = "#ffc23d"
COOL = "#7fb7be"     # cool / below-normal (blue-green, distinguishable from ember)
BURN = [[0, "#241d18"], [0.25, "#4a1d10"], [0.5, "#a3300e"], [0.72, "#e8590c"], [0.88, "#ffa630"], [1, "#fff1b8"]]

CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Archivo:wght@400;600;800&family=Archivo+Narrow:wght@500;700&family=IBM+Plex+Mono:wght@400;500&display=swap');
.stApp, .stMarkdown, .stApp p, .stApp label, .stApp input, .stApp button p { font-family: 'Archivo', sans-serif; }
[data-testid="stIconMaterial"] { font-family: 'Material Symbols Rounded' !important; }
.block-container { padding-top: 1.6rem; max-width: 1280px; }
h1, h2, h3 { font-family: 'Archivo Narrow', sans-serif !important; letter-spacing: .01em; }
[data-testid="stHeader"] { background: transparent; }

.wc-brand { display:flex; align-items:baseline; gap:.9rem; flex-wrap:wrap; margin-bottom:.2rem; }
.wc-brand b { font-family:'Archivo Narrow'; font-weight:700; font-size:2.1rem; letter-spacing:.06em; color:#ece3d4; }
.wc-brand b span { color:#ff6a1a; }
.wc-brand i { font-style:normal; color:#9a8f82; font-size:.95rem; }

.wc-orbit { position:relative; margin:.6rem 0 1.4rem; font-family:'IBM Plex Mono'; font-size:.72rem; color:#9a8f82; }
.wc-orbit .row { display:flex; align-items:center; height:18px; gap:.6rem; }
.wc-orbit .lab { width:118px; flex:none; text-align:right; }
.wc-orbit .track { position:relative; flex:1; height:6px; background:#231d18; border-radius:3px; }
.wc-orbit .bar { position:absolute; top:0; bottom:0; border-radius:3px; }
.wc-orbit .ticks { display:flex; justify-content:space-between; margin-left:calc(118px + .6rem); padding-top:2px; }

.wc-kicker { font-family:'IBM Plex Mono'; font-size:.72rem; letter-spacing:.14em; text-transform:uppercase;
             color:#ff6a1a; margin: 0 0 .25rem; }
.wc-area { font-family:'Archivo Narrow'; font-weight:700; font-size:1.55rem; line-height:1.15; margin:0 0 .35rem; }
.wc-lede { font-size:1.02rem; line-height:1.5; color:#d9cfc0; margin:.2rem 0 1rem; }
.wc-lede em { font-style:normal; color:#ffc23d; }

.wc-read { border-top:1px solid #3a322b; padding:.7rem 0 .55rem; }
.wc-read .k { font-family:'IBM Plex Mono'; font-size:.7rem; letter-spacing:.12em; text-transform:uppercase; color:#9a8f82; }
.wc-read .v { font-family:'IBM Plex Mono'; font-weight:500; font-size:1.45rem; color:#ece3d4; margin-top:.1rem; }
.wc-read .n { font-size:.84rem; color:#9a8f82; margin-top:.1rem; }
.wc-dot { display:inline-block; width:.62rem; height:.62rem; border-radius:50%; margin-right:.45rem; vertical-align:middle; }

.wc-sec { font-family:'IBM Plex Mono'; font-size:.74rem; letter-spacing:.14em; text-transform:uppercase; color:#9a8f82;
          border-bottom:1px solid #3a322b; padding-bottom:.35rem; margin:1.2rem 0 .6rem; }
.wc-sec b { color:#ff6a1a; font-weight:500; margin-right:.6rem; }
.wc-note { font-size:.84rem; color:#9a8f82; }

.stTabs [data-baseweb="tab-list"] { gap: 1.4rem; border-bottom:1px solid #3a322b; }
.stTabs [data-baseweb="tab"] { font-family:'IBM Plex Mono'; font-size:.8rem; letter-spacing:.08em; text-transform:uppercase;
                               padding: .5rem 0; }
[data-testid="stSidebar"] { border-right:1px solid #3a322b; }
.stDownloadButton button, .stButton button { border-radius:2px; border:1px solid #3a322b; }
iframe { border-radius: 2px; }
@media (max-width: 640px) { .wc-orbit { font-size:.6rem; } .wc-orbit .lab { width:84px; white-space:nowrap; }
  .wc-orbit .ticks { margin-left:calc(84px + .6rem); }
  .wc-brand b { font-size:1.6rem; } }
</style>
"""


def esc(s) -> str:
    return html.escape(str(s))


def brand(tagline: str) -> str:
    return f'<div class="wc-brand"><b>WILDFIRE<span>/</span>CALENDAR</b><i>{esc(tagline)}</i></div>'


def orbit(start=2000, end=2026) -> str:
    """Strip showing which satellite sensors were flying when — the reason harmonization is needed."""
    span = end - start

    def bar(a, b, color):
        return (f'<div class="bar" style="left:{100 * (a - start) / span:.2f}%;'
                f'width:{100 * (b - a) / span:.2f}%;background:{color}"></div>')

    rows = [("MODIS · Terra", bar(2000.15, end, "#8a5a3c")),
            ("MODIS · Aqua", bar(2002.5, end, "#8a5a3c")),
            ("VIIRS · S-NPP", bar(2012.05, end, EMBER))]
    body = "".join(f'<div class="row"><div class="lab">{l}</div><div class="track">{b}</div></div>' for l, b in rows)
    ticks = "".join(f"<span>{y}</span>" for y in range(start, end + 1, 5))
    return f'<div class="wc-orbit">{body}<div class="ticks">{ticks}</div></div>'


def readout(key: str, value: str, note: str = "", dot: str | None = None) -> str:
    d = f'<span class="wc-dot" style="background:{dot}"></span>' if dot else ""
    n = f'<div class="n">{note}</div>' if note else ""
    return f'<div class="wc-read"><div class="k">{esc(key)}</div><div class="v">{d}{esc(value)}</div>{n}</div>'


def section(num: str, title: str) -> str:
    return f'<div class="wc-sec"><b>{esc(num)}</b>{esc(title)}</div>'


pio.templates["ember"] = go.layout.Template(layout=dict(
    paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
    font=dict(family="IBM Plex Mono, monospace", color=INK, size=12),
    xaxis=dict(gridcolor="#2a231e", linecolor=LINE, zerolinecolor=LINE, tickcolor=LINE),
    yaxis=dict(gridcolor="#2a231e", linecolor=LINE, zerolinecolor=LINE, tickcolor=LINE),
    colorway=[EMBER, FLAME, COOL, "#c9a27e", "#8a5a3c"],
    hoverlabel=dict(bgcolor=PANEL, bordercolor=LINE, font=dict(family="IBM Plex Mono", color=INK)),
    legend=dict(bgcolor="rgba(0,0,0,0)"),
))
pio.templates.default = "ember"

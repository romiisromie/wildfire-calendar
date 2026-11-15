# Space Apps 2026 project page — text to paste

Challenge: **Harmonization of MODIS and VIIRS Hot Spots**

---

## Project Name

Wildfire Calendar

## High-Level Project Summary

MODIS, the longest satellite fire record (2000–), is reaching the end of its life. Its successor, VIIRS (2012–), sees about twice as much fire, so the two records cannot simply be joined. When we joined them naively, the trend pointed the wrong way in 3 of our 6 test areas. In Corrientes, Argentina, fire appears to rise 81%, while the harmonized record, and MODIS alone, show it fell 19%.

Wildfire Calendar is a web app that harmonizes NASA FIRMS MODIS and VIIRS hotspots into one consistent burning-activity calendar for any area a user draws:

- It learns a month-by-month VIIRS/MODIS conversion for that area.
- It tests the conversion on years it never saw and shows a plain-language trust label.
- It lets emergency managers see the critical periods, compare this month or any fire with the same dates in every year since 2000, check the last 7 days, and download CSV data and PNG charts.

## Link to Project Demo

[paste the public link to the 7-slide deck (PDF on Google Drive or GitHub)]

## Link to Final Project

https://wildfire-calendar.streamlit.app
(source code: https://github.com/romiisromie/wildfire-calendar)

## Detailed Project Description

**What it does.** The user picks an area in one of three ways:

- a ready example (steppe, pine forest and reserve in Kazakhstan; wetlands, grassland, shrubland and Andean forest in Argentina);
- a polygon drawn on the map;
- coordinates plus a radius.

The app then shows:

1. **Calendar**: a month × year (or week × year) heatmap of harmonized fire activity, 2000–2025, in colour scales that read in greyscale and for colour-blind users.
2. **This year vs normal**: each week of the latest year against the median year and the usual 10–90% range. A summary line says, for example, "Dec 2025 burned less than usual (0.3× the median)".
3. **Last 7 days**: the last 7 complete days of near-real-time VIIRS (NOAA-20) against the normal for the same calendar days. The normal comes from S-NPP; the two instruments share a design but are not cross-calibrated here.
4. **Climate & shift**:
   - whether the fire season starts or ends earlier, using a Theil–Sen trend with a Kendall test, cross-checked on MODIS alone so the 2012 sensor change cannot create it;
   - how fire in the next 3 days differs after hot-dry-windy and after calm-humid days (NASA POWER weather), each with a 90% range over the seasons.
5. **Compare & download**: pick any date range (for example a fire in progress) and see it against the same dates in every year since 2000: its rank, the median year, and a bar chart. Download the hotspots of that period, the period-by-year table, the calendar and the daily series as CSV; every chart has a PNG button.
6. **Seasons & events**: the main fire seasons, weeks far above normal, and a check against fires reported in the news.
7. **Harmonization**: what naive joining would conclude vs the harmonized record and MODIS alone, the held-out error, the factor for each month, and VIIRS vs converted MODIS in the overlap years.

The online demo ships Kazakhstan and Argentina. Any other country in the NASA FIRMS archive can be added in the open-source version (`python fetch.py Brazil --build`). The interface is in English, Spanish and Russian.

**How it works.**

1. Keep confident vegetation-fire detections: MODIS confidence ≥ 30, VIIRS nominal or high, type 0 (no volcanoes or static sources).
2. Measure activity as active 0.1° cells per day. This depends less on pixel size than raw detection counts. Hotspot counts and fire radiative power are also available.
3. For the selected area, learn a VIIRS/MODIS factor for each calendar month from 2013–2025. When a month has little fire, the factor is pulled toward the all-year value.
4. Before 4 July 2002 only Terra flew. Those days are scaled by a Terra → Terra+Aqua factor learned from 2003–2011.
5. Days when VIIRS recorded nothing in the whole country while MODIS did are treated as instrument outages and filled from MODIS × factor.
6. **Validation.** Each year 2013–2025 is predicted from MODIS with a factor learned without that year. The error is Σ|predicted − actual| ÷ Σ actual over monthly totals.

**Results.** Held-out error, raw MODIS → our method:

| Area | Raw MODIS | Our method | Trust |
|---|---|---|---|
| Corrientes & Iberá, Argentina | 56% | 11% | High |
| Kostanay steppe, Kazakhstan | 44% | 12% | High |
| Paraná Delta, Argentina | 59% | 30% | Medium |
| Córdoba hills, Argentina | 55% | 31% | Medium |
| Naurzum reserve, Kazakhstan | 43% | 34% | Medium |
| Arakaragai pine forest, Kazakhstan | 54% | 35% | Medium |
| Comarca Andina, Argentina | — | too little fire to test | Insufficient |

Six fires reported in the news each rank as the strongest week of 2013–2025 in their area:

| Fire | VIIRS hotspots ±3 days | Typical year, same dates |
|---|---|---|
| Corrientes, Feb 2022 | 10,821 | 168 |
| Paraná Delta, Aug 2020 | 4,800 | 62 |
| Kostanay steppe, Aug 2015 | 1,734 | 130 |
| Córdoba hills, Oct 2020 | 932 | 46 |
| Arakaragai forest, Sep 2022 | 860 | 0 |
| Las Golondrinas, Chubut, Mar 2021 | 500 | 0 |

Why harmonization matters. Change in yearly fire from 2003–2010 to 2016–2025:

| Area | Sensors joined as they are | Harmonized | Check: MODIS alone |
|---|---|---|---|
| Corrientes & Iberá | **+81%** | −19% | −18% |
| Paraná Delta | **+13%** | −51% | −53% |
| Córdoba hills | **+8%** | −50% | −50% |
| Kostanay steppe | −40% | −66% | −66% |
| Naurzum reserve | −62% | −78% | −77% |
| Arakaragai forest | −54% | −76% | −77% |

What the harmonized record shows:

- **Decline.** Yearly fire in the Kostanay steppe is 66% lower in 2016–2025 than in the 2000s. Each sensor alone shows the same: Terra −65%, Aqua −67% (2003–2010 vs 2016–2025), and VIIRS −37% from 2013–15 to 2023–25. It is not a sensor artefact.
- **Stable ratio.** The yearly VIIRS/MODIS ratio stays between 1.67 and 2.21 over 2013–2025, with no trend. The conversion is therefore not drifting, which supports applying it to the MODIS-only years.
- **Fire weather.** After calm, humid days, fire in the next 3 days is 0.4–0.7× normal, with the 90% range below 1 in 9 of 11 fire seasons. The opposite effect after hot-dry-windy days is significant only in the Córdoba hills (1.6×), and we report it that way.
- **A lead, not a claim.** The Kostanay spring season may be starting earlier (−4.3 days per decade, p = 0.03; MODIS alone −3.6). We test about 30 trends, so we treat this as a lead to check.

**Benefits.**

- Fire and forest services can plan staffing around the real season and see at once whether this season is above normal.
- Reserves get a reliable history of their own territory.
- Scientists get one series with a stated error instead of two sensors to reconcile.
- Every number comes with how far it can be trusted.

**Why now.** MODIS on Terra and Aqua is near the end of its life. Without harmonization, its 25-year fire history cannot be continued with VIIRS.

**What we hope to achieve.** We want a free tool that any fire service, reserve or researcher can open for their own area. As a next step, calibrating NOAA-20 and NOAA-21 against S-NPP would keep the record going as S-NPP ages.

**Tools.** Python, Streamlit, pandas, NumPy, SciPy, PyArrow (Parquet), Plotly, Folium/Leaflet, Streamlit Community Cloud, Git/GitHub.

## Use of Super Intelligence (SI)

The team chose the challenge, the study areas and the validation questions, and directed and checked the work. The application code, the data-processing scripts and the slide layout were written with an AI coding assistant (Claude Code by Anthropic). This is stated in the app's Method tab and in the repository README. No images, audio, video or data were AI-generated. All figures are computed from NASA data, and the screenshots in the slides are of the real app.

## NASA Data

- **NASA FIRMS, MODIS Collection 6.1 active fires (MCD14ML)**, Terra and Aqua, 2000–2025, yearly country archives.
- **NASA FIRMS, VIIRS S-NPP 375 m active fires (VNP14IMGTDL)**, 2012–2025, yearly country archives.
- **NASA FIRMS, VIIRS NOAA-20 375 m near-real-time active fires**, last 7 days.
- **NASA POWER daily point data** (MERRA-2): maximum temperature, relative humidity, wind speed and precipitation, 2000–2026.

## Space Agency Partner Data and Other References

- No Space Agency Partner datasets are used directly. The Argentina study areas and fire events relate to the work of CONAE (National Space Activities Commission of Argentina).
- **Map tiles:** Esri World Dark Gray Canvas (© Esri, HERE, Garmin, © OpenStreetMap contributors).
- **Open-source libraries:** Streamlit, pandas, NumPy, SciPy, PyArrow, Plotly, Folium, streamlit-folium (their own licences).
- **Fonts:** Archivo, Archivo Narrow, IBM Plex Mono (Google Fonts, SIL Open Font License).
- **Methods:** Theil–Sen slope estimator; Kendall rank correlation test; vapour-pressure deficit (Tetens formula); hot-dry-windy index after Srock et al. (2018), *Atmosphere* 9(7):279.
- **Fire events used for validation:** news and agency reports of the Paraná Delta fires (2020), Córdoba hills fires (2020), Las Golondrinas fire, Chubut (2021), Corrientes fires (2022), Kostanay steppe fires (2015) and Arakaragai forest fire (2022). [add the article links you want to cite]

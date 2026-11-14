# Wildfire Calendar — NASA Space Apps 2026

Challenge: **Harmonization of MODIS and VIIRS Hot Spots**.
Built during the hackathon, 14–15 November 2026 (see the git history).

Draw any area and get one 25-year fire record (2000–2025) built from two NASA sensors:

- **Calendar**: a month × year (or week × year) heatmap with a colour-blind-safe palette.
- **This year vs normal**: the latest year's weeks against the median year and the usual 10–90% range.
- **Fire seasons and anomalies**: weeks far above normal, plus a check against fires reported in the news.
- **Harmonization**: a monthly VIIRS/MODIS factor learned for *this* area, tested by leaving one year out at a time. The result is a plain-language trust label (High / Medium / Low / Insufficient).
- **CSV download** of the calendar, the daily series and the raw hotspots.
- **Last 7 days**: today's fires (VIIRS on NOAA-20, near-real-time, no key) against the normal for these dates.
- **Climate & season shift**: is the fire season starting earlier (Theil–Sen trend, cross-checked on MODIS alone), and how much more fire follows hot-dry-windy days (NASA POWER weather).
- **Any country** (open-source version): type a FIRMS country name in the sidebar and the app downloads and builds its 2000–2025 record. The online demo ships Kazakhstan and Argentina.
- **English / Español / Русский** interface (`?lang=ES`).

## Run

```bash
pip install -r requirements.txt
python fetch.py Kazakhstan     # NASA FIRMS yearly country archives, no key needed
python data.py Kazakhstan      # -> data/store/Kazakhstan.parquet
streamlit run app.py
```

## Method

1. **Detections kept**: MODIS confidence ≥ 30 and VIIRS nominal or high; vegetation fires only (type 0).
2. **Activity measure**: active 0.1° cells per day. Hotspot counts and FRP are also available.
3. **Calibration**: k(month) = ΣVIIRS / ΣMODIS over 2013–2025, shrunk toward the all-year k when a month has little fire.
4. **Before July 2002**: only Terra flew, so Terra-only days are scaled by a Terra→Terra+Aqua factor learned from 2003–2011.
5. **VIIRS outage days**: days with no VIIRS detection anywhere in the country while MODIS saw fire are filled from MODIS × k.
6. **Validation**: each year 2013–2025 is predicted from MODIS with k learned without that year. The monthly error sets the trust label: < 20% High, < 40% Medium, otherwise Low.

## Data

- **NASA FIRMS**: MODIS Collection 6.1 (MCD14ML) and VIIRS S-NPP 375 m (VNP14IMGTDL), yearly country archives; VIIRS NOAA-20 7-day near-real-time file.
- **NASA POWER**: daily maximum temperature, humidity, wind and precipitation (MERRA-2).

Kazakhstan and Argentina are included in `data/store/` so the app runs without downloading.

## Use of AI

The code was written with an AI coding assistant (Claude Code, Anthropic) directed by the team.

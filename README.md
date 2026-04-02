# 🌧️ Rainfall Tools

A unified suite of Australian rainfall and soil water analysis tools,
powered by [SILO](https://www.longpaddock.qld.gov.au/silo/) climate data.

## Apps

| Page | Description |
|---|---|
| 📈 How is the season going? | Cumulative rainfall percentile vs all years on record |
| 🎲 What are the odds? | Rolling window rainfall frequency analysis |
| 💧 Howwet | PERFECT/HowLeaky soil water balance model |

## Structure

```
rainfall-tools/
├── Home.py                  # Landing page
├── pages/
│   ├── 1_Season.py          # How is the season going?
│   ├── 2_Odds.py            # What are the odds?
│   └── 3_Howwet.py          # Soil water monitor
├── core/
│   ├── silo.py              # Unified SILO API layer (shared by all pages)
│   ├── waterbalance.py      # PERFECT daily water balance engine
│   ├── soil.py              # Soil profile (.PRM format)
│   ├── soil_xml.py          # Soil profile (.soil XML format)
│   ├── soil_excel.py        # Soil profile (Excel format)
│   ├── vege.py              # Vegetation (.vege XML format)
│   ├── cover_excel.py       # Cover schedule (Excel format)
│   ├── run_simulation.py    # Simulation runner
│   ├── read_p51.py          # SILO .P51 file reader
│   └── perfect_io.py        # PERFECT .MET / .CRP readers
├── data/
│   └── *.soil               # Soil parameter files
├── .streamlit/
│   └── config.toml
└── requirements.txt
```

## Shared core: `core/silo.py`

All three pages use a single SILO module with three public functions:

```python
from core.silo import search_stations, fetch_patched_point, fetch_datadrill

# Station search — used by Season and Odds
stations = search_stations("Roma")

# Patched point by station ID — used by Season and Odds (rainfall only)
df = fetch_patched_point(station_id, "19000101", "20261231")

# DataDrill by lat/lon — used by Howwet (full met variables)
df = fetch_datadrill(lat=-27.28, lon=151.26, start="20050101", end="20261231")
```

## Running locally

```bash
git clone https://github.com/YOUR_USERNAME/rainfall-tools.git
cd rainfall-tools
pip install -r requirements.txt
streamlit run Home.py
```

## Deploying to Streamlit Community Cloud

1. Push repo to GitHub
2. Go to [share.streamlit.io](https://share.streamlit.io)
3. New app → select repo → Main file: `Home.py`
4. Deploy — one URL, all three tools, free

## Data

- **SILO Patched Point Dataset** — station-based daily records back to 1889
- **SILO DataDrill** — gridded interpolated surface for any lat/lon
- Water balance model: PERFECT v2.0 (Littleboy et al. 1992) / HowLeaky
# rainfall-tools

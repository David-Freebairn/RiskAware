"""
core/silo.py
============
SILO Patched Point API helpers used by all pages.

Public API
----------
search_stations(query)          -> list of station dicts
fetch_station_met(station_id, start, end) -> pd.DataFrame
"""

import urllib.parse
import urllib.request
import io
import pandas as pd
import numpy as np
from pathlib import Path

# ── Config ─────────────────────────────────────────────────────────────────
_BASE  = "https://www.longpaddock.qld.gov.au/cgi-bin/silo/PatchedPointDataset.php"
_EMAIL = "david.freebairn@gmail.com"   # SILO requires a registered email


# ── Station search ──────────────────────────────────────────────────────────

def search_stations(query: str) -> list[dict]:
    """
    Search SILO for stations matching a name fragment.

    Returns list of dicts:
        { id: int, name: str, label: str, lat: float, lon: float, state: str }
    """
    url = (f"{_BASE}?format=name"
           f"&nameFrag={urllib.parse.quote(query.strip())}"
           f"&username={urllib.parse.quote(_EMAIL)}")
    try:
        with urllib.request.urlopen(url, timeout=15) as resp:
            raw = resp.read().decode("utf-8", errors="replace")
    except Exception as exc:
        raise RuntimeError(f"SILO station search failed: {exc}") from exc

    stations = []
    for line in raw.strip().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "|" not in line:
            continue
        parts = [p.strip() for p in line.split("|")]
        if len(parts) < 2:
            continue
        try:
            sid   = int(parts[0])
            name  = parts[1].strip()
            lat   = float(parts[2]) if len(parts) > 2 and parts[2] else None
            lon   = float(parts[3]) if len(parts) > 3 and parts[3] else None
            state = parts[4].strip() if len(parts) > 4 else ""
            label = name
            if state:
                label += f"  [{state}]"
            if lat is not None and lon is not None:
                label += f"  ({lat:.3f}, {lon:.3f})"
            stations.append({
                "id":    sid,
                "name":  name,
                "label": label,
                "lat":   lat,
                "lon":   lon,
                "state": state,
            })
        except (ValueError, IndexError):
            continue
    return stations


# ── Fetch met data ──────────────────────────────────────────────────────────

def fetch_station_rainfall(station_id: int, start: str, end: str) -> pd.DataFrame:
    """
    Fetch daily rainfall only from SILO Patched Point.
    Used by 1_Season.py.

    Returns
    -------
    pd.DataFrame indexed by date with columns:
        rain, year, month, day, doy
    """
    df = fetch_station_met(station_id, start, end)
    return df[["rain", "year", "month", "day", "doy"]]


def fetch_patched_point(station_id: int, start: str, end: str) -> pd.DataFrame:
    """
    Fetch full daily met from SILO Patched Point.
    Used by 2_Odds.py.
    Alias for fetch_station_met — returns all climate variables.

    Returns
    -------
    pd.DataFrame indexed by date with columns:
        rain, epan, tmax, tmin, tmean, radiation, vp, year, month, day, doy
    """
    return fetch_station_met(station_id, start, end)


def fetch_station_met(station_id: int, start: str, end: str) -> pd.DataFrame:
    """
    Fetch daily climate from SILO Patched Point for a known station ID.

    Parameters
    ----------
    station_id : int    SILO station number
    start      : str    YYYYMMDD
    end        : str    YYYYMMDD

    Returns
    -------
    pd.DataFrame indexed by date with columns:
        rain, epan, tmax, tmin, tmean, radiation, vp, year, month, day, doy
    """
    url = (f"{_BASE}"
           f"?station={station_id}"
           f"&start={start}&finish={end}"
           f"&format=csv&comment=R"
           f"&username={urllib.parse.quote(_EMAIL)}")
    try:
        with urllib.request.urlopen(url, timeout=90) as resp:
            raw = resp.read().decode("utf-8", errors="replace")
    except Exception as exc:
        raise RuntimeError(
            f"SILO fetch failed for station {station_id} "
            f"({start}–{end}): {exc}"
        ) from exc

    return _parse_patched_point(raw, station_id)


# ── Parser ──────────────────────────────────────────────────────────────────

def _parse_patched_point(text: str, station_id: int) -> pd.DataFrame:
    """
    Parse SILO Patched Point CSV response into a clean DataFrame.
    Handles the variable-length comment header before the data columns.
    """
    lines = text.splitlines()

    # Find the header row — first line with 'date' and commas
    header_idx = None
    for i, line in enumerate(lines):
        low = line.lower()
        if "," in low and ("daily_rain" in low or
                           ("date" in low and "rain" in low)):
            header_idx = i
            break

    if header_idx is None:
        # Check for SILO error messages
        preview = "\n".join(lines[:10])
        if "rejected" in text.lower() or "error" in text.lower():
            raise RuntimeError(
                f"SILO rejected the request for station {station_id}.\n"
                "Check the station ID is valid and try again.\n"
                f"Response preview:\n{preview}"
            )
        raise RuntimeError(
            f"Could not find data header in SILO response "
            f"for station {station_id}.\nPreview:\n{preview}"
        )

    csv_text = "\n".join(lines[header_idx:])
    raw_df = pd.read_csv(io.StringIO(csv_text))
    raw_df.columns = [c.strip().lower() for c in raw_df.columns]

    # Build standardised output
    df = pd.DataFrame()
    df.index = pd.to_datetime(
        raw_df["date"].astype(str), format="%Y%m%d", errors="coerce"
    )
    df.index.name = "date"
    df = df[df.index.notna()]

    df["year"]  = df.index.year
    df["month"] = df.index.month
    df["day"]   = df.index.day
    df["doy"]   = df.index.day_of_year

    # Column name mapping: SILO name -> standard name
    col_map = {
        "daily_rain": "rain",
        "max_temp":   "tmax",
        "min_temp":   "tmin",
        "evap_pan":   "epan",
        "radiation":  "radiation",
        "vp":         "vp",
        "rh_tmax":    "rh_tmax",
        "rh_tmin":    "rh_tmin",
    }
    for silo_col, our_col in col_map.items():
        if silo_col in raw_df.columns:
            df[our_col] = raw_df[silo_col].values
        else:
            df[our_col] = np.nan

    df["tmean"] = (df["tmax"] + df["tmin"]) / 2.0

    # Ensure epan is never NaN (model needs a value)
    if df["epan"].isna().all():
        df["epan"] = 0.0
    else:
        df["epan"] = df["epan"].fillna(0.0)

    df["rain"] = df["rain"].fillna(0.0).clip(lower=0)

    return df

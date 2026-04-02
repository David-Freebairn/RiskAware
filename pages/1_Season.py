"""
pages/1_Season.py — How is the season going?
==============================================
Compares current season's cumulative rainfall against all years on record.
Ported from season_compare.html — SILO calls via core.silo.

Analysis logic (faithful port from JS):
  - Window: last N months, starting 1st of month
  - Each historical year is aligned to the same calendar window
  - Percentile = fraction of comparable years with less rain than current
  - Median series computed day-by-day across all comparable years
  - Chart: spaghetti of historical years + dashed median + bold current year
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import streamlit as st
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import matplotlib.ticker as ticker
import io
from datetime import date, timedelta
from calendar import monthrange

from core.silo import search_stations, fetch_station_rainfall

# ── Page config ───────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="How is the season going?",
    page_icon="📈",
    layout="wide",
)

MONTHS = ["Jan","Feb","Mar","Apr","May","Jun",
          "Jul","Aug","Sep","Oct","Nov","Dec"]

# ── CSS ───────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Merriweather:ital,wght@0,400;0,700;1,400&family=Source+Sans+3:wght@300;400;600&display=swap');
html, body, [class*="css"] { font-family: 'Source Sans 3', sans-serif; }
.page-title {
    font-family: 'Merriweather', serif; font-size: 2.4rem; font-weight: 700;
    color: #1a4a6e; line-height: 1.15; margin-bottom: 2px;
}
.page-subtitle {
    font-family: 'Merriweather', serif; font-style: italic;
    font-size: 1.05rem; color: #555; margin-bottom: 12px;
}
.result-headline {
    font-family: 'Merriweather', serif; font-size: 1.05rem;
    color: #1a1a1a; line-height: 1.8;
    border: 2px solid #ccc; border-radius: 4px;
    padding: 16px 22px; background: #fff; margin-bottom: 16px;
}
.rank { font-size: 1.9rem; font-weight: 700; color: #1a4a6e; vertical-align: baseline; }
.diff-above { font-size: 0.9rem; font-weight: 600; border-radius: 3px;
              padding: 2px 8px; background: #eaf5ea; color: #1a6a1a; }
.diff-below { font-size: 0.9rem; font-weight: 600; border-radius: 3px;
              padding: 2px 8px; background: #fdf0e8; color: #8a3a00; }
.r-site { font-size: 0.88rem; color: #555; letter-spacing: 0.03em; }
.chip-row { display: flex; gap: 8px; flex-wrap: wrap; margin: 8px 0 16px 0; }
.chip { background: #f0f5fb; border: 1px solid #c0d4e8; border-radius: 3px;
        padding: 3px 10px; font-size: 0.82rem; color: #2a4a6a; }
.chip b { color: #1a1a1a; }
</style>
""", unsafe_allow_html=True)


# ── Helpers ───────────────────────────────────────────────────────────────────

@st.cache_data(ttl=3600, show_spinner=False)
def _search(query: str):
    return search_stations(query)


@st.cache_data(ttl=3600, show_spinner=False)
def _fetch(station_id: int, start: str, end: str) -> pd.DataFrame:
    return fetch_station_rainfall(station_id, start, end)


def days_in_month(y: int, m: int) -> int:
    return monthrange(y, m)[1]


def build_series(df: pd.DataFrame, months_back: int):
    """
    Build cumulative rainfall series for every historical year aligned
    to the same calendar window as the current season.

    Returns
    -------
    series      : dict  end_year -> pd.Series (cumulative rain, DatetimeIndex)
    current_year: int
    median_ser  : pd.Series  day-by-day median across comparable years (same index as current)
    pctile      : int   percentile rank of current year (0-100)
    diff_mm     : int   mm above (+) or below (-) median at today
    stats       : dict  summary stats for chips
    """
    today  = df.index.max().date()
    end_y  = today.year
    end_m  = today.month
    end_d  = today.day

    # Window start = 1st of month, months_back months ago
    start_m = end_m - months_back
    start_y = end_y
    while start_m <= 0:
        start_m += 12
        start_y -= 1

    year_offset = end_y - start_y  # 0 or positive integer

    # Build fast lookup: (year, month, day) -> rain
    lookup = {}
    for idx, row in df.iterrows():
        lookup[(idx.year, idx.month, idx.day)] = row["rain"]

    data_years = sorted(df.index.year.unique())
    min_data_y = data_years[0]

    series = {}
    first_end_y = min_data_y + year_offset

    for ey in range(first_end_y, end_y + 1):
        sy = ey - year_offset
        is_current = (ey == end_y)
        cum = 0.0
        dates, cums = [], []
        missing_streak = 0

        wy, wm, wd = sy, start_m, 1
        stop_m = end_m
        stop_d = end_d if is_current else days_in_month(ey, end_m)

        ok = True
        while True:
            if wy > ey: break
            if wy == ey and wm > stop_m: break
            if wy == ey and wm == stop_m and wd > stop_d: break

            rain = lookup.get((wy, wm, wd), None)
            if rain is None:
                if not is_current:
                    missing_streak += 1
                    if missing_streak > 5:
                        ok = False
                        break
                rain = 0.0
            else:
                missing_streak = 0

            cum += rain
            dates.append(pd.Timestamp(wy, wm, wd))
            cums.append(cum)

            wd += 1
            if wd > days_in_month(wy, wm):
                wd = 1; wm += 1
            if wm > 12:
                wm = 1; wy += 1

        if ok and dates:
            s = pd.Series(cums, index=dates)
            series[ey] = s

    if not series or end_y not in series:
        return None, end_y, None, None, None, None

    current = series[end_y]
    current_total = float(current.iloc[-1])
    n_current = len(current)

    # Comparable years: not current year, has at least as many days
    comp_years  = [y for y in series if y != end_y and len(series[y]) >= n_current]
    comp_totals = [float(series[y].iloc[n_current - 1]) for y in comp_years]

    if not comp_years:
        return series, end_y, None, None, None, None

    better = sum(1 for t in comp_totals if t > current_total)
    pctile = round((1 - better / len(comp_years)) * 100)

    # Median series — day by day
    median_vals = []
    current_dates = current.index
    for i in range(n_current):
        vals = sorted([float(series[y].iloc[i]) for y in comp_years if len(series[y]) > i])
        if not vals:
            median_vals.append(np.nan)
            continue
        mid = len(vals) // 2
        med = (vals[mid - 1] + vals[mid]) / 2 if len(vals) % 2 == 0 else vals[mid]
        median_vals.append(med)

    median_ser  = pd.Series(median_vals, index=current_dates)
    median_final = float(median_ser.iloc[-1])
    diff_mm = round(current_total - median_final)

    # Summary stats
    ann_totals = df.groupby(df.index.year)["rain"].sum()
    stats = {
        "period"    : f"{data_years[0]}–{data_years[-1]}",
        "ann_mean"  : round(float(ann_totals.mean())),
        "ann_max"   : round(float(ann_totals.max())),
        "n_years"   : len(data_years),
        "curr_total": round(current_total),
    }
    return series, end_y, median_ser, pctile, diff_mm, stats


def make_chart(series, current_year, median_ser, station_name,
               months_back, start_year_from):
    """
    Spaghetti chart: historical years (light blue) + median (dashed dark blue)
    + current year (bold red). X-axis = calendar dates aligned to current window.
    """
    C_HIST    = "#7ab4d8"
    C_MEDIAN  = "#1a4a6e"
    C_CURRENT = "#cc2200"
    C_BG      = "#ffffff"
    C_GRID    = "#e0e8f0"

    plt.rcParams.update({
        "font.family"        : "sans-serif",
        "axes.facecolor"     : C_BG,
        "figure.facecolor"   : C_BG,
        "axes.spines.top"    : False,
        "axes.spines.right"  : False,
        "axes.linewidth"     : 0.8,
    })

    fig, ax = plt.subplots(figsize=(12, 4.5))

    current = series[current_year]

    # All historical years
    for ey, s in series.items():
        if ey == current_year:
            continue
        # Align historical dates to current window dates for plotting
        n = min(len(s), len(current))
        ax.plot(current.index[:n], s.values[:n],
                color=C_HIST, lw=0.9, alpha=0.45, zorder=1)

    # Median
    if median_ser is not None:
        ax.plot(median_ser.index, median_ser.values,
                color=C_MEDIAN, lw=2, ls="--", zorder=3, label="Median")
        # Label at end
        last_valid = median_ser.dropna()
        if len(last_valid):
            ax.annotate(
                "median",
                xy=(last_valid.index[-1], last_valid.iloc[-1]),
                xytext=(6, 0), textcoords="offset points",
                fontsize=8, color=C_MEDIAN, va="center",
            )

    # Current year
    ax.plot(current.index, current.values,
            color=C_CURRENT, lw=2.5, zorder=4,
            label=f"{current_year} (current)")
    ax.plot(current.index[-1], current.values[-1],
            "o", color=C_CURRENT, ms=7, mfc="none", mew=2, zorder=5)

    # Today vertical line
    ax.axvline(current.index[-1], color="#888", lw=1, ls=":", zorder=2)

    # Axes
    ax.set_ylabel("Cumulative rainfall (mm)", fontsize=10, color="#555")
    ax.set_ylim(bottom=0)
    ax.yaxis.set_major_locator(ticker.MaxNLocator(nbins=5, integer=True))
    ax.tick_params(labelsize=9)
    ax.grid(axis="y", color=C_GRID, lw=0.7, zorder=0)

    # X-axis — calendar-aligned labels
    n_months = months_back
    if n_months <= 14:
        ax.xaxis.set_major_locator(mdates.MonthLocator())
        ax.xaxis.set_major_formatter(mdates.DateFormatter("%b\n%Y"))
    elif n_months <= 30:
        ax.xaxis.set_major_locator(mdates.MonthLocator(bymonth=[1,4,7,10]))
        ax.xaxis.set_major_formatter(mdates.DateFormatter("%b %Y"))
    else:
        ax.xaxis.set_major_locator(mdates.MonthLocator(bymonth=[1,7]))
        ax.xaxis.set_major_formatter(mdates.DateFormatter("%b %Y"))

    ax.tick_params(axis="x", labelsize=8.5)
    plt.setp(ax.xaxis.get_majorticklabels(), ha="center")

    ax.set_title(
        f"{station_name}   ·   looking back {months_back} months",
        fontsize=11, color="#1a2332", pad=8, loc="left",
    )

    plt.tight_layout(pad=1.2)
    return fig


def ordinal(n: int) -> str:
    s = ["th","st","nd","rd"] + ["th"] * 16
    return f"{n}{s[n % 20] if n % 20 < 4 else 'th'}"


# ── UI ────────────────────────────────────────────────────────────────────────

st.markdown("""
<div class="page-title">📈 How is the season going?</div>
<div class="page-subtitle">Comparing this season's rainfall against all years on record</div>
""", unsafe_allow_html=True)

# ── Step 1: Select site ───────────────────────────────────────────────────────
with st.container(border=True):
    st.markdown("**Select site**")

    col1, col2 = st.columns([1.5, 2.5])
    with col1:
        query = st.text_input(
            "station", label_visibility="collapsed",
            placeholder="Search station — e.g. Roma, Cairns",
            key="se_query",
        )
    with col2:
        start_year = st.number_input(
            "Records from year", min_value=1889,
            max_value=date.today().year, value=1900, step=1,
            help="Earliest year to include in the historical comparison",
        )

    station_info = None
    if query and len(query) >= 3:
        if st.session_state.get("se_last_query") != query:
            with st.spinner("Searching..."):
                try:
                    st.session_state["se_stations"] = _search(query)
                except Exception as e:
                    st.error(f"Search failed: {e}")
                    st.session_state["se_stations"] = []
            st.session_state["se_last_query"] = query
            st.session_state["se_sel_idx"]    = 0

        stations = st.session_state.get("se_stations", [])
        if stations:
            labels = [s["label"] for s in stations]
            if len(labels) == 1:
                st.success(f"✅ {labels[0]}")
                station_info = stations[0]
                st.session_state["se_saved"] = station_info
            else:
                confirmed = st.session_state.get("se_confirmed", False)
                chosen    = st.session_state.get("se_chosen") or labels[0]
                if chosen not in labels:
                    chosen = labels[0]
                if confirmed:
                    c1, c2 = st.columns([6, 1])
                    with c1:
                        st.success(f"📍 {chosen}")
                    with c2:
                        if st.button("Change", key="se_change"):
                            st.session_state["se_confirmed"] = False
                    station_info = next(s for s in stations if s["label"] == chosen)
                else:
                    st.caption(f"**{len(labels)} stations found** — select one:")
                    def _pick():
                        st.session_state["se_chosen"]    = st.session_state["se_radio"]
                        st.session_state["se_confirmed"] = True
                    chosen = st.radio(
                        "Station", labels,
                        index=labels.index(chosen) if chosen in labels else 0,
                        key="se_radio", label_visibility="collapsed",
                        on_change=_pick,
                    )
                    st.session_state["se_chosen"] = chosen
                    station_info = next(s for s in stations if s["label"] == chosen)
                st.session_state["se_saved"] = station_info
        elif st.session_state.get("se_last_query"):
            st.warning("No stations found — try a shorter name.")

# ── Step 2: Select duration ───────────────────────────────────────────────────
with st.container(border=True):
    st.markdown("**Select duration**")
    col1, col2, col3 = st.columns([2.5, 1, 2])
    with col1:
        st.markdown("How does the last")
    with col2:
        months_back = st.number_input(
            "months", label_visibility="collapsed",
            min_value=1, max_value=60, value=6, step=1,
        )
    with col3:
        st.markdown("months compare with all years?")

col_l, col_c, col_r = st.columns([1, 2, 1])
with col_c:
    run_clicked = st.button(
        "Run analysis",
        type="primary",
        disabled=(station_info is None),
        use_container_width=True,
    )

# ── Analysis ──────────────────────────────────────────────────────────────────
if run_clicked or st.session_state.get("se_result"):
    if run_clicked:
        if station_info is None:
            station_info = st.session_state.get("se_saved")
        if station_info is None:
            st.error("Please select a station.")
            st.stop()

        sid  = station_info["id"]
        name = station_info["name"]
        end_str   = date.today().strftime("%Y%m%d")
        start_str = f"{int(start_year)}0101"

        with st.spinner(f"Fetching data for {name}..."):
            try:
                df = _fetch(sid, start_str, end_str)
            except Exception as e:
                st.error(f"Data fetch failed: {e}")
                st.stop()

        # Filter to requested start year
        df = df[df.index.year >= int(start_year)]
        if df.empty:
            st.error("No data found for this station and period.")
            st.stop()

        st.session_state["se_result"] = {
            "df": df, "name": name, "station_info": station_info,
        }
    else:
        res  = st.session_state["se_result"]
        df   = res["df"]
        name = res["name"]
        station_info = res.get("station_info", {})

    # Summary chips
    ann_totals = df.groupby(df.index.year)["rain"].sum()
    data_years = sorted(df.index.year.unique())
    st.markdown(f"""
    <div class="chip-row">
      <div class="chip"><b>{name}</b></div>
      <div class="chip"><b>{data_years[0]}–{data_years[-1]}</b> period</div>
      <div class="chip">Annual mean <b>{int(ann_totals.mean())} mm</b></div>
      <div class="chip">Annual max <b>{int(ann_totals.max())} mm</b></div>
    </div>
    """, unsafe_allow_html=True)

    # Run analysis
    with st.spinner("Analysing..."):
        series, current_year, median_ser, pctile, diff_mm, stats = build_series(
            df, int(months_back)
        )

    if series is None:
        st.warning("Not enough data for this window.")
        st.stop()

    if pctile is None:
        st.warning("Not enough comparable years to calculate a percentile.")
        st.stop()

    # Result headline
    diff_cls  = "diff-above" if diff_mm >= 0 else "diff-below"
    diff_sign = "+" if diff_mm >= 0 else ""
    diff_dir  = "above" if diff_mm >= 0 else "below"
    min_y, max_y = data_years[0], data_years[-1]

    st.markdown(f"""
    <div class="result-headline">
      Current rainfall looking back <b>{months_back} month{'s' if months_back != 1 else ''}</b>
      is in the &nbsp;<span class="rank">{ordinal(pctile)} percentile</span>
      &nbsp;<span class="{diff_cls}">({diff_sign}{diff_mm} mm {diff_dir} avg)</span>
      <br>
      <span class="r-site">{name} &nbsp;&nbsp; ({min_y}–{max_y})</span>
    </div>
    """, unsafe_allow_html=True)

    # Chart
    fig = make_chart(series, current_year, median_ser, name,
                     int(months_back), int(start_year))

    # Add suptitle for export
    today_label = date.today().strftime("%d %b %Y")
    fig.suptitle(
        f"{name}  ·  Last {months_back} months  ·  "
        f"{ordinal(pctile)} percentile  ·  {diff_sign}{diff_mm} mm {diff_dir} avg  ·  {today_label}",
        fontsize=9, color="#555", y=1.01,
    )

    st.pyplot(fig, use_container_width=True)

    # Export
    buf = io.BytesIO()
    fig.savefig(buf, format="jpeg", dpi=150, bbox_inches="tight", facecolor="white")
    buf.seek(0)
    st.download_button(
        "⬇  Export JPEG",
        data=buf,
        file_name=f"season_{name.replace(' ', '_')}_{months_back}mo.jpg",
        mime="image/jpeg",
    )
    plt.close(fig)

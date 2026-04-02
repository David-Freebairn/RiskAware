"""
core/styles.py
==============
Shared Streamlit CSS injected on every page via apply_styles().

Fixes included
--------------
- Page title / subtitle never truncate — they wrap naturally
- Section titles, result boxes, status messages consistent across pages
- Removes Streamlit default top-padding that wastes header space
"""

import streamlit as st


def apply_styles():
    """Inject shared CSS into the current Streamlit page."""
    st.markdown(_CSS, unsafe_allow_html=True)


_CSS = """
<style>

/* ── Remove excessive top padding Streamlit adds ────────────────────── */
.block-container {
    padding-top: 1.2rem !important;
    padding-bottom: 2rem !important;
    max-width: 1100px;
}

/* ── Page title — never truncate, wraps on small screens ────────────── */
.page-title,
.page-title * {
    font-size: clamp(1.35rem, 3vw, 2rem) !important;
    font-weight: 700 !important;
    color: #1A2F6B !important;
    line-height: 1.25 !important;
    margin-bottom: 0.2rem !important;
    white-space: normal !important;
    overflow: visible !important;
    text-overflow: unset !important;
    max-width: 100% !important;
    width: 100% !important;
}

.page-subtitle,
.page-subtitle * {
    font-size: clamp(0.85rem, 2vw, 1rem) !important;
    color: #555 !important;
    font-style: italic !important;
    margin-bottom: 1rem !important;
    white-space: normal !important;
    overflow: visible !important;
    text-overflow: unset !important;
    max-width: 100% !important;
}

/* Also fix Streamlit's own h1/h2 if used directly */
.stMarkdown h1,
.stMarkdown h2 {
    white-space: normal !important;
    overflow: visible !important;
    text-overflow: unset !important;
}

/* Fix the markdown container itself not clipping */
.stMarkdown,
.element-container {
    overflow: visible !important;
    min-width: 0;
}

/* ── Section headings inside containers ─────────────────────────────── */
.section-title {
    font-size: 1rem;
    font-weight: 600;
    color: #1A5276;
    margin-bottom: 0.4rem;
}

/* ── Result box ──────────────────────────────────────────────────────── */
.result-box {
    background: #F0F4FA;
    border: 1px solid #C5D5E8;
    border-radius: 10px;
    padding: 1.1rem 1.4rem;
    margin-bottom: 1rem;
}

.result-title {
    font-size: 1rem;
    color: #1a2332;
    margin-bottom: 0.4rem;
}

.date-loc { font-weight: 600; }
.loc      { font-weight: 700; color: #1A2F6B; }

.fallow-label {
    font-size: 0.9rem;
    color: #555;
    margin-bottom: 0.5rem;
}

.paw-big {
    font-size: 3rem;
    font-weight: 800;
    color: #1A3A6B;
    line-height: 1;
}

.paw-unit {
    font-size: 1.4rem;
    color: #1A3A6B;
    margin-left: 4px;
}

.pawc-pct {
    font-size: 1.1rem;
    color: #555;
    margin-left: 12px;
}

/* ── Status / spinner messages ───────────────────────────────────────── */
.status-msg {
    font-size: 0.9rem;
    color: #1A5276;
    font-style: italic;
}

/* ── Tighten Streamlit radio / selectbox labels ──────────────────────── */
div[data-testid="stRadio"] label,
div[data-testid="stSelectbox"] label {
    font-size: 0.9rem;
}

/* ── Container borders slightly softer ───────────────────────────────── */
div[data-testid="stVerticalBlockBorderWrapper"] {
    border-radius: 10px !important;
    border-color: #D0DCF0 !important;
}

/* ── Divider thinner ────────────────────────────────────────────────── */
hr {
    margin: 0.6rem 0 !important;
    border-color: #E8EDF5 !important;
}

</style>
"""

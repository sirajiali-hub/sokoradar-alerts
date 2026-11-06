"""Cached loaders shared by every page.

Files are read from alerts_app/data/ (filled by prepare_data.py). When a file is
missing there, the loader falls back to the repo's handoff and raw data folders,
so the app also runs straight after 01_eda_review and 05_alerts.
"""
import json
from pathlib import Path

import pandas as pd
import streamlit as st

APP_DIR = Path(__file__).resolve().parents[1]
DATA = APP_DIR / "data"
KEYS = ["admin2", "market", "crop", "pricetype"]


def find(name):
    if (DATA / name).exists():
        return DATA / name
    for root in [APP_DIR, *APP_DIR.parents]:
        for sub in ("output/modelling/handoff", "sokoradar_raw_data", "handoff"):
            if (root / sub / name).exists():
                return root / sub / name
    return None


def _key(s):
    return s.astype(str).str.lower().str.replace(r"[^a-z]", "", regex=True)


def require(*names):
    missing = [n for n in names if find(n) is None]
    if missing:
        st.error("Some data files are missing: " + ", ".join(missing) +
                 ". Run 01_eda_review and 05_alerts, then `python prepare_data.py`.")
        st.stop()


@st.cache_data
def get_meta():
    return json.load(open(find("meta.json")))


@st.cache_data
def get_counties():
    p = find("counties.csv")
    if p is None:
        return None
    c = pd.read_csv(p)
    c["key"] = _key(c["county"])
    return c[["key", "county", "pcode", "asal"]]


@st.cache_data
def get_alps():
    """One row per market, crop, price type and month with its ALPS score and phase."""
    ca = pd.read_csv(find("county_alps.csv"))
    ca["month"] = pd.PeriodIndex(ca["month"], freq="M")
    ca["key"] = _key(ca["admin2"])
    cty = get_counties()
    if cty is not None:
        ca = ca.merge(cty[["key", "pcode", "asal"]], on="key", how="left")
    else:
        ca["pcode"], ca["asal"] = None, None
    ca["asal"] = ca["asal"].fillna("Unknown")
    return ca


@st.cache_data
def get_prices():
    """Monthly real price series per market, keyed by (county, market, crop, price type)."""
    led = pd.read_csv(find("real_ledger.csv"))
    led["month"] = pd.PeriodIndex(led["month"], freq="M")
    led = led.groupby(KEYS + ["month"], as_index=False)["kes_kg"].mean()
    out = {}
    for key, g in led.groupby(KEYS):
        s = g.set_index("month")["kes_kg"]
        out[key] = s.reindex(pd.period_range(s.index.min(), s.index.max(), freq="M"))
    return out


@st.cache_data
def get_climate():
    """3 month rainfall and vegetation as % of normal, by county pcode and month."""
    p = find("county_climate_chirps_ndvi.csv")
    if p is None:
        return None
    cl = pd.read_csv(p)
    cl["month"] = pd.to_datetime(cl["month"]).dt.to_period("M")
    cols = [c for c in ("rain_3m_pct", "ndvi_pct") if c in cl.columns]
    return cl.rename(columns={"county_pcode": "pcode"})[["pcode", "month", *cols]]


def _area(ring):
    return sum(x1 * y2 - x2 * y1 for (x1, y1, *_), (x2, y2, *_) in zip(ring, ring[1:]))


def _clockwise(polygon):
    """Plotly draws a shape correctly only when the outer ring runs clockwise and holes run the other way."""
    return [r[::-1] if (_area(r) > 0) == (i == 0) else r for i, r in enumerate(polygon)]


@st.cache_data
def get_geo():
    p = find("ken_counties.geojson")
    if p is None:
        return None
    gj = json.load(open(p))
    for f in gj["features"]:
        g = f["geometry"]
        if g["type"] == "Polygon":
            g["coordinates"] = _clockwise(g["coordinates"])
        elif g["type"] == "MultiPolygon":
            g["coordinates"] = [_clockwise(poly) for poly in g["coordinates"]]
    return gj


@st.cache_data
def get_forecasts():
    """Optional: saved by the modelling notebook. Columns: admin2, market, crop, pricetype,
    month, forecast, lower, upper (and alert_prob if available)."""
    p = find("forecasts.csv")
    if p is None:
        return None
    fc = pd.read_csv(p)
    fc["month"] = pd.PeriodIndex(fc["month"], freq="M")
    return fc


@st.cache_data
def get_ew():
    """Early warning predictions from 05_alerts Step 8 (optional)."""
    p = find("ew_predictions.csv")
    if p is None:
        return None
    ew = pd.read_csv(p, usecols=KEYS + ["month", "p_any", "warn", "y_any", "alps", "source"])
    ew["month"] = pd.PeriodIndex(ew["month"], freq="M")
    return ew


@st.cache_data
def get_ew_metrics():
    p = find("ew_metrics.json")
    return json.load(open(p)) if p is not None else None


@st.cache_data
def get_ew_events():
    p = find("ew_events.csv")
    if p is None:
        return None
    ev = pd.read_csv(p)
    ev["month"] = pd.PeriodIndex(ev["month"], freq="M")
    return ev


def ew_threshold():
    m = get_ew_metrics()
    return float(m["threshold"]) if m else None


def rain_for(pcode, month):
    cl = get_climate()
    if cl is None or pcode is None or pd.isna(pcode):
        return None
    r = cl[(cl["pcode"] == pcode) & (cl["month"] == month)]
    return float(r["rain_3m_pct"].iloc[0]) if len(r) and "rain_3m_pct" in r else None

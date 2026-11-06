"""Copy the small files the app needs into alerts_app/data/, so the app can be deployed.

Run once after 01_eda_review and 05_alerts (Step 3), from the alerts_app folder:
    python prepare_data.py
"""
import shutil
from pathlib import Path

import pandas as pd

APP = Path(__file__).resolve().parent
OUT = APP / "data"
OUT.mkdir(exist_ok=True)


def locate(name):
    for root in [APP, *APP.parents]:
        for sub in ("output/modelling/handoff", "sokoradar_raw_data", "handoff"):
            if (root / sub / name).exists():
                return root / sub / name
    return None


needed = ["meta.json", "county_alps.csv", "real_ledger.csv"]
optional = ["counties.csv", "county_climate_chirps_ndvi.csv", "ken_counties.geojson",
            "ew_predictions.csv", "ew_events.csv", "ew_metrics.json", "forecasts.csv"]

for name in needed + optional:
    src = locate(name)
    if src is None:
        print(("MISSING (required): " if name in needed else "not found (optional): ") + name)
        continue
    dst = OUT / name
    if name == "county_climate_chirps_ndvi.csv":       # keep only what the app uses
        cl = pd.read_csv(src)
        keep = [c for c in ("county_pcode", "month", "rain_3m_pct", "ndvi_pct") if c in cl.columns]
        cl[keep].to_csv(dst, index=False)
    elif name == "ew_predictions.csv":                  # keep only what the app uses
        ew = pd.read_csv(src)
        keep = ["admin2", "market", "crop", "pricetype", "month", "p_any", "warn", "y_any", "alps", "source"]
        ew[keep].round(4).to_csv(dst, index=False)
    else:
        shutil.copy(src, dst)
    print(f"copied {name:35s} {dst.stat().st_size / 1e6:5.2f} MB")

print("\nDone. Start the app with: python -m streamlit run app.py")

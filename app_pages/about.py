"""Data, method, patterns in the data, limits and feedback."""
import pandas as pd
import plotly.express as px
import streamlit as st

from src import charts, style
from src.alerts import COLOURS, PHASES
from src.loaders import get_alps, get_climate, get_meta, require
from src.views import phase_share

require("meta.json", "county_alps.csv", "real_ledger.csv")

style.setup()
style.hero("About & limits", "Where the data comes from, how alerts work, what the data shows, and what to keep in mind.",
           step="4 · Trust the numbers")
meta, ca = get_meta(), get_alps()
latest = ca["month"].max()

tab_what, tab_method, tab_patterns, tab_limits = st.tabs(["What it does", "How alerts work", "Patterns in the data", "Limits"])

with tab_what:
    st.markdown(f"""
SokoRadar is an early warning system for food price shocks in Kenyan markets. It shows which markets have
unusually high prices for **maize, beans, sorghum and potatoes** now, which are **likely to in the next 3 months**,
explains why in plain words, suggests what to do, and gives county teams a list and a printable bulletin.

**Who it is for**
* **County governments and NDMA:** which counties to watch, and when to act.
* **WFP, Red Cross and NGOs:** where and when to adjust cash and food support. The markets still reporting in 2026
  include the Kakuma and Dadaab refugee camps, where these programmes run.
* **Farmers (future channel):** our real prices are mostly retail prices in towns and camps, so we do not give farmers
  sell or store advice yet. With KAMIS data from five markets in every county, the same warnings could reach them by SMS.

**Data:** WFP market prices from 2006 to {latest.strftime('%B %Y')}, real prices only, plus CHIRPS rainfall by county.
""")
    cov = ca.groupby("crop").agg(markets=("market", "nunique"), counties=("admin2", "nunique"),
                                 first=("month", "min"), last=("month", "max")).reset_index()
    cov[["first", "last"]] = cov[["first", "last"]].astype(str)
    st.dataframe(cov, hide_index=True, width="stretch",
                 column_config={"crop": "Crop", "markets": "Markets", "counties": "Counties",
                                "first": "First month", "last": "Latest month"})

with tab_method:
    st.markdown("""
**Alert phases (WFP ALPS method).** For each market, we learn the normal price for each time of year from a
long term trend and the usual monthly pattern, using **earlier months only**, so no month ever uses future data.
The ALPS score says how far today's price sits above that normal level, measured in the usual size of price swings.
""")
    st.table(pd.DataFrame({
        "Phase": ["Normal", "Stress", "Alert", "Crisis"],
        "ALPS score": ["below 0.25", "0.25 to 1", "1 to 2", "2 and above"],
        "Meaning": ["Price is about normal", "Price is starting to rise", "Price is unusually high",
                    "Price is very high: act now"],
    }))
    st.markdown(f"""
**Early warning.** A gradient boosting model estimates the chance that each market hits Alert or Crisis within the
next 3 months, from what is known that month: how far the price is above normal now and recently, recent price moves,
county rainfall and vegetation, dry spells, the time of year, other prices in the county and how many markets are in
alert nationally. It is tested year by year, each year predicted by a model trained only on earlier years.

**Training and test years.** Everything is set on {meta['TRAIN'][0]} to {meta['TRAIN'][1]} and checked once on
{meta['TEST'][0]} to {meta['TEST'][1]}.

**Choosing the alert threshold.** Missing a real crisis costs more than a false alarm, so the threshold is chosen to
catch most real shocks while keeping false alarms manageable. The project target is to catch at least 70% of Alert and
Crisis months, with at least half of alerts being correct.
""")

with tab_patterns:
    hist_src = get_alps()
    train_end = pd.Period(get_meta()["TRAIN"][1], freq="M")
    hist = hist_src[hist_src["month"] <= train_end]
    st.caption(f"Based on real market prices up to {train_end.strftime('%B %Y')} (the training years).")

    # ---- Compare groups ------------------------------------------------------------
    by = st.selectbox("Compare how often prices hit Alert or Crisis by",
                      ["crop", "asal", "admin2", "pricetype"],
                      format_func={"crop": "Crop", "asal": "Dry land class (ASAL)", "admin2": "County",
                                   "pricetype": "Retail or wholesale"}.get)
    seg = (hist.assign(hit=hist["phase"].isin(["Alert", "Crisis"]))
               .groupby(by).agg(share=("hit", "mean"), months=("hit", "size"), markets=("market", "nunique"))
               .reset_index().sort_values("share", ascending=False))
    seg = seg[seg["months"] >= 24]
    fig = px.bar(seg, x=by, y="share", hover_data=["months", "markets"], color_discrete_sequence=["#ef6c00"],
                 labels={"share": "Share of months in Alert or Crisis", by: ""},
                 title="How often prices are unusually high")
    fig.update_layout(yaxis_tickformat=".0%", height=360, margin=dict(t=40, b=10))
    st.plotly_chart(fig, width="stretch")
    st.caption("Only groups with at least 24 market months are shown.")

    # ---- Over time -------------------------------------------------------------------
    st.markdown("**When do shocks happen?**")
    st.plotly_chart(charts.share_chart(phase_share(by="crop")), width="stretch")
    st.caption("Peaks line up with drought years such as 2011, 2017 and 2021 to 2022: many markets hit Alert at once.")

    # ---- Rainfall and alerts ------------------------------------------------------------
    st.markdown("**What comes with alerts: rainfall**")
    cl = get_climate()
    if cl is None or "rain_3m_pct" not in cl:
        st.info("Rainfall data is not available.")
    else:
        j = hist.merge(cl, on=["pcode", "month"], how="inner")
        r = j.groupby("phase", observed=True)["rain_3m_pct"].mean().reindex(PHASES).dropna().reset_index()
        fig = px.bar(r, x="phase", y="rain_3m_pct", color="phase", color_discrete_map=COLOURS,
                     labels={"rain_3m_pct": "Average 3 month rainfall (% of normal)", "phase": ""},
                     title="Rainfall in the 3 months before each phase")
        fig.add_hline(y=100, line_dash="dot", line_color="grey", annotation_text="normal rainfall")
        fig.update_layout(showlegend=False, height=340, margin=dict(t=40, b=10))
        st.plotly_chart(fig, width="stretch")
        st.caption("If Alert and Crisis months have lower rainfall than Normal months, dry spells are a useful early warning sign. "
                   "The EDA found a dry spell adds about 15 percentage points to the 3 month maize price rise.")

with tab_limits:
    st.markdown("""
* **Real prices only.** National prices for 2022 to 2024 are mostly estimates. Including them created many false
  Crisis months (maize: 27 Crisis months with estimates, 5 on real prices), so this app shows real market prices only.
* **A calm test period.** 2025 to 2026 had very few alert months (12 across 44 market series). Test scores alone
  cannot prove the alerts work, so past droughts (2011, 2017, 2022) are replayed as extra evidence.
* **Gaps in coverage.** Many counties have no regular real market prices. They appear grey on the map, not green.
* **Reasons on the market page are rule based.** The model's overall drivers are on *Does it work?*;
  per market drivers (SHAP) will be added with the forecasting model.
* **2011 replay.** Too little data exists before 2011 for a strict backtest, so 2011 uses a model trained on every other
  training year with the drought left out. 2017 and 2022 use the strict year by year backtest.
* **Household cost** uses an adjustable monthly quantity, not survey data. Bag prices use common bag sizes (90 kg, 50 kg
  for potatoes).
* **Price alerts are one input.** NDMA drought phases combine many indicators (rainfall, vegetation, livestock, nutrition);
  SokoRadar adds an early price signal to that picture, it does not replace it.
* **Not trading advice.** Alerts are early warnings to support planning, published to everyone at the same time.
""")

st.divider()
st.markdown("Was this app useful?")
st.feedback("thumbs", key="feedback_about")
st.caption("Sources: WFP via HDX (CC BY-IGO), CHIRPS rainfall, Ministry of Agriculture, KNBS, CBK. "
           "Built by Group 10, Moringa School Data Science.")

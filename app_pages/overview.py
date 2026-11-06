"""This month: where are food prices unusually high, where are they likely to be soon, and what to do."""
import pandas as pd
import streamlit as st

from src import charts, style
from src.actions import action, bulletin_html, outlook
from src.loaders import ew_threshold, get_alps, get_ew_metrics, get_geo, rain_for, require
from src.views import county_status, market_table

require("meta.json", "county_alps.csv", "real_ledger.csv")
style.setup()
style.hero("SokoRadar", "Early warning for food price shocks in Kenyan markets, for county teams, NDMA and NGOs.",
           step="1 · This month: where to act")

ca, metrics, thr_default = get_alps(), get_ew_metrics(), ew_threshold()
line = style.lead_sentence(metrics)
if line:
    style.headline(line)

with st.expander("How to use"):
    st.markdown(
        "1. Pick a month and a crop. The latest month shows live warnings for the next 3 months.\n"
        "2. **Map:** which counties are in Alert now, or likely to be within 3 months.\n"
        "3. **Action list:** markets to act on, with the reason and a suggested action. Download it for your report.\n"
        "4. **County bulletin:** a one page summary to print or forward.\n"
        "5. Open **Market check** to see one market in detail."
    )

# ---- Inputs ------------------------------------------------------------------
months = sorted(ca["month"].unique(), reverse=True)
c1, c2 = st.columns(2)
month = c1.selectbox("Month", months, format_func=lambda p: p.strftime("%B %Y"))
crop = c2.selectbox("Crop", ["All crops"] + sorted(ca["crop"].unique()))
st.session_state["month"], st.session_state["crop"] = month, crop

with st.sidebar:
    st.header("Settings")
    if thr_default is not None:
        thr = st.slider("Early warning threshold (chance)", 0.05, 0.95,
                        st.session_state.get("ew_threshold", round(thr_default, 2)), 0.01,
                        help="Markets at or above this chance of hitting Alert within 3 months get an early warning. "
                             "The default was chosen on the training years, with a missed crisis counted 5 times a false alarm.")
        st.session_state.ew_threshold = thr
        st.caption("Lower catches more real shocks but raises more false alarms. See **Does it work?**")
    else:
        thr = None
        st.info("Early warnings appear after running Steps 4 to 8 of 05_alerts and prepare_data.py.")

try:
    with st.spinner("Checking markets..."):
        table = market_table(str(month), crop).copy()
        prev = market_table(str(month - 1), crop)
except Exception as exc:  # never show a stack trace to users
    st.error(f"Something went wrong while reading the market data: {exc}.")
    st.stop()

if table.empty:
    st.info("No market reported a real price for this crop in this month. Try another month or crop.")
    st.stop()

if thr is not None:   # the sidebar threshold overrides the default
    table["outlook"] = [outlook(p, thr) for p in table["p_any"]]
    table["action"] = [action(ph, p, thr) for ph, p in zip(table["phase"], table["p_any"])]
hot = table["phase"].isin(["Alert", "Crisis"])
warn = (table["p_any"] >= thr) if thr is not None else pd.Series(False, index=table.index)
prev_hot = int(prev["phase"].isin(["Alert", "Crisis"]).sum()) if not prev.empty else 0
on_list = table[hot | warn]
diff = int(hot.sum()) - prev_hot

style.cards([
    ("Markets reporting", f"{len(table):,}", f"Real WFP prices, {month.strftime('%B %Y')}", None),
    ("In Alert or Crisis now", f"{int(hot.sum()):,}",
     f"{diff:+d} vs last month" if diff else "same as last month", "#c62828"),
    ("Early warnings, next 3 months", f"{int((warn & ~hot).sum()):,}" if thr is not None else "n/a",
     "not in Alert yet, but likely soon", "#ef6c00"),
    ("Counties affected", f"{on_list['admin2'].nunique():,}", "in Alert or with an early warning", None),
])
st.write("")

tab_map, tab_list, tab_bulletin = st.tabs(["Map", "Action list", "County bulletin"])

with tab_map:
    mode = st.radio("Show", ["Alerts now", "Early warnings for the next 3 months"], horizontal=True,
                    disabled=thr is None)
    status = county_status(month, crop, "warn" if mode.startswith("Early") else "now")
    st.plotly_chart(charts.county_map(status, get_geo(), f"{mode}, {month.strftime('%B %Y')}"), width="stretch")
    st.caption("Grey counties have no real market prices this month, so no alert is shown for them.")

with tab_list:
    show = table[["admin2", "market", "crop", "pricetype", "price", "gap", "phase", "p_any", "main_reason", "action"]].copy()
    show["p_any"] = 100 * show["p_any"]
    st.dataframe(
        show, hide_index=True, width="stretch",
        column_config={
            "admin2": "County", "market": "Market", "crop": "Crop", "pricetype": "Type",
            "price": st.column_config.NumberColumn("KES/kg", format="%.0f"),
            "gap": st.column_config.NumberColumn("vs normal", format="%+.0f%%"),
            "phase": "Phase now",
            "p_any": st.column_config.ProgressColumn("Chance of Alert in 3 months", format="%.0f%%",
                                                     min_value=0, max_value=100),
            "main_reason": "Main reason", "action": "Suggested action",
        },
    )
    st.download_button(f"Download action list ({len(on_list):,} markets)",
                       on_list.drop(columns=["pcode", "rank"], errors="ignore").round(3).to_csv(index=False),
                       f"sokoradar_action_list_{month}.csv", "text/csv", disabled=on_list.empty)
    st.caption("Markets in Crisis or Alert come first, then those most likely to hit Alert soon. "
               "The download includes markets in Alert or Crisis now and markets with an early warning.")

with tab_bulletin:
    b1, b2 = st.columns([2, 1], vertical_alignment="bottom")
    county = b1.selectbox("County", sorted(table["admin2"].unique()))
    pc = table.loc[table["admin2"] == county, "pcode"].iloc[0]
    rain = rain_for(pc, month)
    page = bulletin_html(county, month, table, thr, rain)
    b2.download_button("Download bulletin (open and print)", page,
                       f"sokoradar_bulletin_{county}_{month}.html", "text/html", width="stretch")
    st.caption("A one page summary for county meetings: status, markets to watch, reasons and suggested actions.")
    # preview: same page, with its styles scoped so they do not change the rest of the app
    css = page[page.find("<style>"):page.find("</style>") + 8]
    css = (css.replace("body{", ".sr-bulletin{").replace("h1{", ".sr-bulletin h1{").replace("table{", ".sr-bulletin table{")
              .replace("th,td{", ".sr-bulletin th,.sr-bulletin td{").replace("th{", ".sr-bulletin th{")
              .replace(".badge{", ".sr-bulletin .badge{").replace(".note{", ".sr-bulletin .note{"))
    body = page.split("<body>")[1].split("</body>")[0]
    with st.container(border=True):
        st.html(css + f'<div class="sr-bulletin" style="margin:8px">{body}</div>')

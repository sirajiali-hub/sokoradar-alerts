"""Market check: one market explained. Why it is flagged, what it costs a household, the SMS a trader or
family would get, and what happened after similar rainfall."""
import pandas as pd
import streamlit as st

from src import charts, style
from src.actions import BAG_KG, HOUSEHOLD_KG, action, outlook, sms
from src.alerts import normal_line, rainfall_what_if, reasons
from src.loaders import KEYS, ew_threshold, get_alps, get_climate, get_forecasts, get_prices, require
from src.views import market_table

require("meta.json", "county_alps.csv", "real_ledger.csv")
style.setup()
style.hero("Market check", "One market explained: why it is flagged, what it costs a household, and what to tell people.",
           step="2 · Explain one market")

ca = get_alps()
thr = st.session_state.get("ew_threshold", ew_threshold())
months = sorted(ca["month"].unique(), reverse=True)
default_month = st.session_state.get("month", months[0])

c1, c2, c3 = st.columns(3)
month = c1.selectbox("Month", months, index=months.index(default_month) if default_month in months else 0,
                     format_func=lambda p: p.strftime("%B %Y"))
table = market_table(str(month), "All crops")
if table.empty:
    st.info("No market reported a real price in this month. Pick another month.")
    st.stop()
county = c2.selectbox("County", list(dict.fromkeys(table["admin2"])), help="Counties with the most urgent markets first.")
sub = table[table["admin2"] == county].reset_index(drop=True)
labels = [f"{r.market} · {r.crop} · {r.pricetype}" for r in sub.itertuples()]
pick = c3.selectbox("Market and crop", range(len(sub)), format_func=lambda i: labels[i])
row = sub.iloc[pick].copy()
row["action"] = action(row["phase"], row["p_any"], thr)

key = tuple(row[k] for k in KEYS)
price = get_prices()[key]
normal, score = normal_line(price)
look = outlook(row["p_any"], thr)

# ---- Headline ---------------------------------------------------------------------
style.headline(
    f"{style.badge(row['phase'])} &nbsp; <b>{row['crop']} in {row['market']}</b> costs <b>KES {row['price']:.0f}/kg</b>, "
    f"{abs(row['gap']):.0f}% {'above' if row['gap'] >= 0 else 'below'} its normal level for {month.strftime('%B')}. "
    f"Chance of Alert or Crisis in the next 3 months: <b>{look.lower()}</b>"
    + (f" ({row['p_any']:.0%})." if pd.notna(row["p_any"]) else "."))

bag = BAG_KG.get(row["crop"])
style.cards([
    ("Price now", f"KES {row['price']:.0f}/kg", f"normal for {month.strftime('%B')}: KES {row['normal']:.0f}", None),
    (f"Per {bag} kg bag" if bag else "Per bag", f"KES {row['price'] * bag:,.0f}" if bag else "n/a",
     f"{(row['price'] - row['normal']) * bag:+,.0f} vs normal" if bag else "", None),
    ("ALPS score", f"{row['score']:.1f}", "Alert from 1, Crisis from 2", None),
    ("Next 3 months", look, "early warning model", "#ef6c00" if look == "High" else None),
])
st.write("")

left, right = st.columns(2)
with left:
    st.subheader("Why")
    for r in reasons(row, row["crop"], month, row["rain"])[:3]:
        st.markdown(f"- {r}")
    st.markdown(f"**Suggested action:** {row['action']}")
    st.caption("Reasons come from simple, transparent rules. The model's overall drivers are on **Does it work?**")

with right:
    st.subheader("What it costs a household")
    kg = st.number_input(f"Household buys this much {row['crop'].lower()} a month (kg)", 1, 200,
                         HOUSEHOLD_KG.get(row["crop"], 20), 1, help="Change this to match the county.")
    extra = (row["price"] - row["normal"]) * kg
    if extra > 0:
        st.markdown(f"A household buying {kg} kg a month pays about **KES {extra:,.0f} more** than in a normal "
                    f"{month.strftime('%B')}.")
    else:
        st.markdown(f"A household buying {kg} kg a month pays about KES {abs(extra):,.0f} **less** than normal.")

    st.subheader("Message for traders and families (SMS)")
    en, sw = sms(row.to_dict(), row["crop"], row["market"], month, row["p_any"], thr)
    st.code(en, language=None, wrap_lines=True)
    st.code(sw, language=None, wrap_lines=True)
    st.caption(f"{len(en)} and {len(sw)} characters (one SMS holds 160). Ready for the SMS and USSD channel.")

st.subheader("Price against its normal level")
fc = get_forecasts()
if fc is not None:
    fc = fc[(fc[KEYS] == pd.Series(key, index=KEYS)).all(axis=1)]
st.plotly_chart(charts.price_chart(price, normal, fc), width="stretch")
if fc is None:
    st.caption("Price forecasts for the next 1 to 3 months will be added here from the team's forecasting model.")
st.plotly_chart(charts.score_chart(score), width="stretch")

st.subheader("What-if: what happened after a dry or wet season here?")
cl = get_climate()
if cl is None or pd.isna(row["pcode"]):
    st.info("Rainfall data is not available for this county.")
else:
    rain = cl[cl["pcode"] == row["pcode"]].set_index("month")["rain_3m_pct"]
    now = row["rain"] if pd.notna(row["rain"]) else 100.0
    w1, w2, w3 = st.columns([2, 1, 1])
    level = w1.slider("Rainfall over 3 months (% of normal)", 0, 200, int(round(now)), 5)
    w = rainfall_what_if(price, rain, level)
    if w is None or w["n"] < 3:
        w2.info("Not enough months with this rainfall in this market's history.")
    else:
        w2.metric("Typical 3 month change", f"{w['all']:+.0f}%", help=f"Average over {w['n_all']} months")
        w3.metric("After similar rainfall", f"{w['near']:+.0f}%", f"{w['near'] - w['all']:+.0f} pts",
                  delta_color="inverse", help=f"Based on {w['n']} past months")
    st.caption("Based on what happened in this market after similar rainfall in the past. It is not a forecast.")

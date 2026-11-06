"""Does it work? Drought replays with lead time, and honest results against simple rules."""
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from src import charts, style
from src.loaders import get_alps, get_ew_events, get_ew_metrics, get_geo, require
from src.views import county_status, phase_share, warning_share

require("meta.json", "county_alps.csv", "real_ledger.csv")
style.setup()
style.hero("Does it work?", "How early SokoRadar warns in real droughts, and how it compares with simple rules.",
           step="3 · The proof")

ca, m, events = get_alps(), get_ew_metrics(), get_ew_events()
if m is None:
    st.info("Run Steps 4 to 8 of 05_alerts.ipynb, then `python prepare_data.py`, to see the results.")
    st.stop()

line = style.lead_sentence(m)
if line:
    style.headline(line)

bt = pd.DataFrame(m["backtest"]).set_index("target")
ew = bt.loc["y_any"]
all_lead = next((r for r in m["lead"] if r["period"] == "All backtest years"), None)
style.cards([
    ("Real alerts caught (recall)", f"{ew['recall model']:.0%}", f"'stays in Alert' rule: {ew['recall same as now']:.0%}", "#2e7d32"),
    ("Warnings that came true", f"{ew['precision model']:.0%}", f"'stays in Alert' rule: {ew['precision same as now']:.0%}", None),
    ("New alerts warned early", f"{all_lead['share warned early']:.0%}" if all_lead else "n/a", "WFP current alert: 0%", "#ef6c00"),
    ("Average warning", f"{all_lead['average lead when warned (months)']:.1f} months" if all_lead else "n/a",
     "before the alert started", "#ef6c00"),
])
y0, y1 = m["backtest_years"]
st.caption(f"Every number comes from predictions the model had not seen: a year by year backtest ({y0} to {y1}, each year "
           f"predicted by a model trained only on earlier years) and a final test on 2025 to 2026 run once. Project targets: "
           f"recall of at least 70% with precision of at least 50%, and warnings at least one month before WFP's current alert.")

months = sorted(ca["month"].unique())
EPISODES = {"2011 drought": ("2010-10", "2011-12", "2011-06"), "2017 drought": ("2016-10", "2017-12", "2017-03"),
            "2022 drought": ("2021-10", "2022-12", "2022-06")}

tabs = st.tabs(["Drought replay", "Against simple rules", "Choosing the threshold", "By crop and area",
                "Are the chances honest?", "What drives warnings"])

with tabs[0]:
    c1, c2 = st.columns([1, 3])
    crop = c1.selectbox("Crop", ["All crops"] + sorted(ca["crop"].unique()))
    preset = c1.radio("Jump to", [*EPISODES, "Latest month"])
    default = pd.Period(EPISODES[preset][2], freq="M") if preset in EPISODES else months[-1]
    if default not in months:
        default = months[-1]
    month = c2.select_slider("Month", options=months, value=default, format_func=lambda p: p.strftime("%b %Y"))

    # ---- Lead time headline -------------------------------------------------------
    if m and preset in EPISODES:
        row = next((r for r in m["lead"] if r["period"] == preset), None)
        if row and row["new alerts"]:
            st.subheader(f"{preset}: how early did SokoRadar warn?")
            k1, k2, k3, k4 = st.columns(4)
            k1.metric("New alerts in this drought", f"{row['new alerts']:.0f}",
                      help="Markets that moved into Alert or Crisis after at least 3 calm months.")
            k2.metric("Warned at least 1 month early", f"{row['share warned early']:.0%}",
                      f"{row['warned 1+ months early']:.0f} of {row['new alerts']:.0f}", delta_color="off", delta_arrow="off")
            k3.metric("Average warning", f"{row['average lead when warned (months)']:.1f} months",
                      "WFP current alert: 0 months", delta_color="off", delta_arrow="off")
            k4.metric("Warnings that came true", f"{row['warnings that came true']:.0%}",
                      help="Share of SokoRadar warnings in this period followed by Alert or Crisis within 3 months.")
            if preset == "2011 drought":
                st.caption("2011 uses a model trained on every other training year (the drought itself left out), "
                           "because too little data exists before it. 2017 and 2022 use the strict year by year backtest.")

    mode = st.radio("Map shows", ["Alerts that month", "SokoRadar early warnings that month"], horizontal=True,
                    disabled=m is None)
    status = county_status(month, crop, "warn" if mode.startswith("SokoRadar") else "now")
    st.plotly_chart(charts.county_map(status, get_geo(), f"{mode}, {month.strftime('%B %Y')}"), width="stretch")

    share = warning_share(crop)
    if share is None:
        share = phase_share(crop, by=None)
    st.plotly_chart(charts.share_chart(share, month, "Share of markets: in Alert or Crisis, and warned by SokoRadar "
                                                     "(3 month average)"), width="stretch")
    st.caption("If the warning line rises before the alert line, SokoRadar gave time to act. The red line marks the "
               "month on the map.")

    if events is not None and preset in EPISODES:
        s, e, _ = EPISODES[preset]
        ev = events[(events["month"] >= pd.Period(s, "M")) & (events["month"] <= pd.Period(e, "M"))]
        if crop != "All crops":
            ev = ev[ev["crop"] == crop]
        with st.expander(f"Every new alert in the {preset} ({len(ev)})"):
            st.dataframe(ev.assign(month=ev["month"].astype(str))[["admin2", "market", "crop", "pricetype", "month", "lead"]],
                         hide_index=True, width="stretch",
                         column_config={"admin2": "County", "market": "Market", "crop": "Crop", "pricetype": "Type",
                                        "month": "Alert started", "lead": st.column_config.NumberColumn(
                                            "Months of warning", help="0 = no early warning")})

    lead_box = st.expander("Lead time for every period")

with tabs[1]:
    names = {"y1": "Alert in 1 month", "y2": "Alert in 2 months", "y3": "Alert in 3 months", "y_any": "Alert within 3 months"}
    t = bt.rename(index=names)[["events", "AUC model", "AUC ALPS now", "recall model", "precision model",
                                "recall same as now", "precision same as now", "threshold"]]
    st.dataframe(t, width="stretch", column_config={c: st.column_config.NumberColumn(format="%.2f") for c in t.columns if c != "events"})
    st.markdown("**Same as now** is the rule \"a market in Alert stays in Alert\". It is hard to beat one month ahead, but "
                "it can never warn **before** an alert starts. That is where SokoRadar adds value (see Lead time).")
    test = m.get("test") or {}
    st.subheader("Final test, 2025 to 2026 (run once)")
    if test:
        st.dataframe(pd.DataFrame([test]).round(2), hide_index=True, width="stretch")
        n = int(test.get("events", 0))
        st.caption(f"{n} Alert months had a known outcome in the test period. "
                   + ("That is very few (the period was calm), so one hit or miss moves these numbers a lot and the "
                      "backtest above is the main evidence." if n < 50 else
                      "Compare these with the backtest: similar numbers mean the warnings held up on new data."))
    else:
        st.info("The test period had no Alert months with a known outcome, so recall cannot be measured there.")

with tabs[2]:
    c = pd.DataFrame(m["curve"])
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=c["threshold"], y=c["recall"], name="Real alerts caught (recall)"))
    fig.add_trace(go.Scatter(x=c["threshold"], y=c["precision"], name="Warnings that came true (precision)"))
    fig.add_vline(x=m["threshold"], line_dash="dash", line_color="grey", annotation_text="chosen")
    fig.update_layout(height=340, xaxis_title="Early warning threshold (chance)", yaxis_tickformat=".0%",
                      legend_orientation="h", margin=dict(t=20, b=10))
    st.plotly_chart(fig, width="stretch")
    fig2 = px.line(c, x="threshold", y="cost", labels={"cost": f"Total cost (miss = {m['cost_miss']}, false alarm = 1)"})
    fig2.add_vline(x=m["threshold"], line_dash="dash", line_color="grey")
    fig2.update_layout(height=260, margin=dict(t=20, b=10))
    st.plotly_chart(fig2, width="stretch")
    st.caption("A lower threshold catches more real shocks but raises more false alarms. The chosen threshold has the "
               "lowest total cost on the training years. Try other values with the slider on This month.")

with tabs[3]:
    for key, title in [("by_crop", "crop"), ("by_asal", "asal")]:
        g = pd.DataFrame(m[key])
        if g.empty:
            continue
        g = g.rename(columns={title: "group"})
        fig = px.bar(g.melt(id_vars="group", value_vars=["recall", "precision"]), x="group", y="value", color="variable",
                     barmode="group", labels={"value": "", "group": "", "variable": ""},
                     title="By crop" if title == "crop" else "By dry land class (ASAL)")
        fig.update_layout(height=300, yaxis_tickformat=".0%", margin=dict(t=40, b=10), legend_orientation="h")
        st.plotly_chart(fig, width="stretch")
    st.caption("Checks whether the warnings work as well for every crop and for arid counties, where people are most exposed.")

with tabs[4]:
    cal = pd.DataFrame(m["calibration"])
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=[0, 1], y=[0, 1], mode="lines", line_dash="dot", line_color="grey", name="perfect"))
    fig.add_trace(go.Scatter(x=cal["predicted"], y=cal["observed"], mode="lines+markers", name="SokoRadar",
                             text=cal["rows"], hovertemplate="predicted %{x:.0%}, observed %{y:.0%}, %{text} rows"))
    fig.update_layout(height=360, xaxis_title="Predicted chance", yaxis_title="Share that actually hit Alert",
                      xaxis_tickformat=".0%", yaxis_tickformat=".0%", margin=dict(t=20, b=10))
    st.plotly_chart(fig, width="stretch")
    st.caption("Points above the line mean the model is too careful, below the line too alarmed. The model weights the "
               "rare Alert months more heavily, so read the chance as a ranking and a warning level, not an exact probability.")

with tabs[5]:
    imp = pd.DataFrame(m["importance"]).head(10)
    fig = px.bar(imp.iloc[::-1], x="importance", y="driver", orientation="h",
                 labels={"importance": "Drop in ranking quality when this information is hidden", "driver": ""},
                 color_discrete_sequence=["#ef6c00"])
    fig.update_layout(height=380, margin=dict(t=20, b=10))
    st.plotly_chart(fig, width="stretch")
    top = imp["driver"].iloc[0] if len(imp) else ""
    st.caption(f"Measured by hiding one piece of information at a time on 2019 to 2024 and seeing how much worse the "
               f"warnings get. The model relies most on: {top.lower()}. Information that overlaps (rainfall, dry spell and "
               f"vegetation) shares its credit, so each can look small on its own.")

with lead_box:
    lead = pd.DataFrame(m["lead"]).set_index("period")
    st.dataframe(lead, width="stretch", column_config={
        "share warned early": st.column_config.NumberColumn(format="percent"),
        "warnings that came true": st.column_config.NumberColumn(format="percent"),
        "average lead when warned (months)": st.column_config.NumberColumn(format="%.1f")})
    st.markdown("A **new alert** is a market moving into Alert or Crisis after at least 3 calm months. WFP's current ALPS "
                "flags it in that month, so it gives **0 months** of warning. Read the lead time together with "
                "*warnings that came true*: a system that warned every month would catch everything early but be useless.")
    st.caption("2011 uses a model trained on every other training year with the drought left out. All other rows use the "
               "strict year by year backtest.")

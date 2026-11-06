"""Plotly charts used by the pages."""
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

from src.alerts import COLOURS, PHASES, to_phase

MAP_COLOURS = {**COLOURS, "Early warning": "#ef6c00", "No warning": "#a5d6a7"}
ORDER = {"phase": PHASES + ["Early warning", "No warning", "No data"]}


def county_map(status, geo, title):
    """status: one row per county with columns pcode, county, phase, detail."""
    if geo is not None and status["pcode"].notna().any():
        # Counties drawn as plain filled shapes: works offline and on any computer, with no map tiles needed.
        info = status.dropna(subset=["pcode"]).set_index("pcode")
        fig, shown = go.Figure(), set()
        for f in geo["features"]:
            pc = f["properties"].get("pcode")
            row = info.loc[pc] if pc in info.index else None
            phase = row["phase"] if row is not None else "No data"
            name = row["county"] if row is not None else f["properties"].get("county", pc)
            hover = f"<b>{name}</b><br>{phase}<br>{row['detail'] if row is not None else 'No real market prices'}"
            g = f["geometry"]
            polys = g["coordinates"] if g["type"] == "MultiPolygon" else [g["coordinates"]]
            for poly in polys:
                xs, ys = zip(*[(pt[0], pt[1]) for pt in poly[0]])
                fig.add_trace(go.Scatter(x=xs, y=ys, fill="toself", mode="lines", line=dict(color="white", width=0.8),
                                         fillcolor=MAP_COLOURS.get(phase, "#bdbdbd"), name=phase, legendgroup=phase,
                                         showlegend=phase not in shown, legendrank=ORDER["phase"].index(phase) if phase in ORDER["phase"] else 99,
                                         hoveron="fills", text=hover, hoverinfo="text"))
                shown.add(phase)
        fig.update_xaxes(visible=False)
        fig.update_yaxes(visible=False, scaleanchor="x", scaleratio=1)
        fig.update_layout(title=title, height=600, margin=dict(l=0, r=0, t=40, b=0), plot_bgcolor="white",
                          legend=dict(traceorder="normal", title_text=""))
        return fig
    d = status.assign(rank=status["phase"].map({**{p: i + 1 for i, p in enumerate(PHASES)}, "No warning": 1,
                                                "Early warning": 3}).fillna(0)).sort_values("rank")
    fig = px.bar(d, x="rank", y="county", color="phase", orientation="h", color_discrete_map=MAP_COLOURS,
                 category_orders=ORDER, hover_data={"rank": False, "detail": True},
                 title=title + " (add ken_counties.geojson to see the map)")
    fig.update_layout(height=max(320, 24 * len(d)), xaxis_visible=False, yaxis_title=None, legend_title_text="")
    return fig


def price_chart(price, normal, fc=None):
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=price.index.to_timestamp(), y=price.values, name="Actual price",
                             mode="lines+markers", marker_size=3, line_color="#1f77b4"))
    fig.add_trace(go.Scatter(x=normal.index.to_timestamp(), y=normal.values, name="Normal level",
                             line=dict(dash="dot", color="grey")))
    if fc is not None and len(fc):
        x = list(fc["month"].dt.to_timestamp())
        fig.add_trace(go.Scatter(x=x + x[::-1], y=list(fc["upper"]) + list(fc["lower"])[::-1], fill="toself",
                                 fillcolor="rgba(239,108,0,0.2)", line_width=0, name="80% range"))
        fig.add_trace(go.Scatter(x=x, y=fc["forecast"], name="Forecast", line_color="#ef6c00"))
    fig.update_layout(title="Price in KES per kg", height=340, margin=dict(t=40, b=10), legend_orientation="h")
    return fig


def score_chart(score):
    s = score.dropna()
    fig = go.Figure(go.Bar(x=s.index.to_timestamp(), y=s.values,
                           marker_color=[COLOURS[p] for p in to_phase(s)]))
    for y, lab in [(1, "Alert"), (2, "Crisis")]:
        fig.add_hline(y=y, line_dash="dash", line_color="grey", annotation_text=lab)
    fig.update_layout(title="ALPS score over time", height=260, margin=dict(t=40, b=10))
    return fig


def share_chart(share, month=None, title="Share of markets in Alert or Crisis (3 month average)"):
    """share: DataFrame indexed by month, one column per line."""
    d = share.copy()
    d.index = d.index.to_timestamp()
    fig = px.line(d, labels={"value": "share of markets", "month": "", "variable": ""}, title=title)
    if month is not None:
        fig.add_vline(x=month.to_timestamp(), line_color="#c62828")
    fig.update_layout(height=300, margin=dict(t=40, b=10), yaxis_tickformat=".0%", legend_orientation="h")
    return fig

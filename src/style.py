"""Shared look: page header, headline banner, phase badges and simple cards."""
import html

import streamlit as st

from src.alerts import COLOURS

CSS = """
<style>
.block-container {padding-top: 2.2rem; max-width: 1250px;}
.sr-hero {background: linear-gradient(120deg, #3e2723 0%, #bf360c 100%); color: #fff; border-radius: 14px;
          padding: 22px 26px; margin-bottom: 18px;}
.sr-hero h1 {color: #fff; font-size: 2.0rem; margin: 0 0 4px 0; padding: 0;}
.sr-hero p {color: #ffe0b2; margin: 0; font-size: 1.02rem;}
.sr-headline {background: #fff3e0; border-left: 6px solid #ef6c00; border-radius: 8px; padding: 12px 16px;
              margin: 4px 0 16px 0; font-size: 1.02rem;}
.sr-badge {display: inline-block; padding: 2px 10px; border-radius: 999px; color: #fff; font-weight: 600; font-size: .85rem;}
.sr-card {border: 1px solid #eee; border-radius: 12px; padding: 14px 16px; background: #fff; height: 100%;}
.sr-card .k {color: #6d6d6d; font-size: .85rem; margin-bottom: 2px;}
.sr-card .v {font-size: 1.7rem; font-weight: 700; line-height: 1.2;}
.sr-card .s {color: #6d6d6d; font-size: .82rem; margin-top: 2px;}
.sr-step {color: #bf360c; font-weight: 700; letter-spacing: .04em; font-size: .8rem; text-transform: uppercase;}
</style>
"""


def setup():
    st.markdown(CSS, unsafe_allow_html=True)


def hero(title, subtitle, step=None):
    step_html = f'<div class="sr-step" style="color:#ffcc80">{html.escape(step)}</div>' if step else ""
    st.markdown(f'<div class="sr-hero">{step_html}<h1>{html.escape(title)}</h1><p>{html.escape(subtitle)}</p></div>',
                unsafe_allow_html=True)


def headline(text_html):
    st.markdown(f'<div class="sr-headline">{text_html}</div>', unsafe_allow_html=True)


def badge(phase):
    return f'<span class="sr-badge" style="background:{COLOURS.get(phase, "#9e9e9e")}">{html.escape(str(phase))}</span>'


def cards(items):
    """items: list of (label, value, small text, colour or None)."""
    cols = st.columns(len(items))
    for col, (label, value, small, colour) in zip(cols, items):
        border = f"border-top: 5px solid {colour};" if colour else ""
        col.markdown(f'<div class="sr-card" style="{border}"><div class="k">{html.escape(label)}</div>'
                     f'<div class="v">{html.escape(str(value))}</div><div class="s">{html.escape(small or "")}</div></div>',
                     unsafe_allow_html=True)


def lead_sentence(metrics):
    """The panel headline, built from the saved results so it always matches the data."""
    if not metrics:
        return None
    row = next((r for r in metrics.get("lead", []) if r["period"] == "All backtest years"), None)
    if not row or not row.get("new alerts"):
        return None
    y0, y1 = metrics["backtest_years"]
    return (f"Tested year by year on {y0} to {y1} data it had never seen, SokoRadar warned of "
            f"<b>{row['warned 1+ months early']:.0f} of {row['new alerts']:.0f} new market alerts "
            f"({row['share warned early']:.0%}) about {row['average lead when warned (months)']:.0f} months before they began</b>. "
            f"WFP's current alert gives no advance warning. {row['warnings that came true']:.0%} of SokoRadar's warnings "
            f"were followed by an alert.")

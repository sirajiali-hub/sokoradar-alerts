"""Turning alerts into action: suggested steps, bag prices, household cost, SMS text in English and
Kiswahili, and the printable county bulletin."""
import html

import pandas as pd

BAG_KG = {"Maize": 90, "Beans": 90, "Sorghum": 90, "Potatoes": 50}   # common market bag sizes in Kenya
HOUSEHOLD_KG = {"Maize": 30, "Beans": 10, "Sorghum": 15, "Potatoes": 20}  # default monthly use, editable in the app

SW_CROP = {"Maize": "Mahindi", "Beans": "Maharagwe", "Sorghum": "Mtama", "Potatoes": "Viazi"}
SW_PHASE = {"Normal": "Kawaida", "Stress": "Shinikizo", "Alert": "Tahadhari", "Crisis": "Hatari"}


def outlook(p, thr):
    """Plain label for the chance of Alert or Crisis in the next 3 months."""
    if p is None or pd.isna(p) or thr is None:
        return "Not available"
    return "High" if p >= thr else ("Medium" if p >= thr / 2 else "Low")


def action(phase, p=None, thr=None):
    if phase == "Crisis":
        return "Act now: request cash transfer top ups, check NCPB reserves, brief the county steering group."
    if phase == "Alert":
        return "Review cash transfer values and step up market monitoring to weekly."
    if outlook(p, thr) == "High":
        return "Early warning: prepare contingency plans and watch this market closely."
    if phase == "Stress":
        return "Watch closely and check again next month."
    return "Routine monitoring."


def short_reason(d, crop, month):
    rain, chg3, gap = d.get("rain"), d.get("chg3"), d.get("gap")
    if rain is not None and pd.notna(rain) and rain < 75:
        return "low rains", "mvua chache"
    if pd.notna(chg3) and chg3 >= 10:
        return "prices rising fast", "bei zinapanda haraka"
    if crop == "Maize" and month.month in (5, 6, 7):
        return "lean season", "msimu wa uhaba"
    if pd.notna(gap) and gap > 0:
        return "above the seasonal normal", "juu ya kawaida ya msimu"
    return "prices near normal", "bei karibu na kawaida"


def sms(d, crop, market, month, p, thr):
    """Two short messages for farmers and traders (aim for one SMS, 160 characters)."""
    gap = d.get("gap")
    en_r, sw_r = short_reason(d, crop, month)
    look = outlook(p, thr)
    sw_look = {"High": "mkubwa", "Medium": "wa wastani", "Low": "mdogo"}.get(look)
    if pd.notna(gap):
        en_gap = f"{abs(gap):.0f}% {'above' if gap >= 0 else 'below'} normal"
        sw_gap = f"{'juu' if gap >= 0 else 'chini'} kwa {abs(gap):.0f}% kuliko kawaida"
    else:
        en_gap = sw_gap = ""
    en = f"SokoRadar: {crop} {market} KES {d['price']:.0f}/kg, {en_gap} ({d['phase']})."
    sw = f"SokoRadar: {SW_CROP.get(crop, crop)} {market} KES {d['price']:.0f}/kg, {sw_gap} ({SW_PHASE.get(d['phase'], d['phase'])})."
    if sw_look:
        en += f" Risk next 3 months: {look.lower()}."
        sw += f" Uwezekano wa bei juu miezi 3: {sw_look}."
    en += f" Reason: {en_r}."
    sw += f" Sababu: {sw_r}."
    return en, sw


def bulletin_html(county, month, table, thr, rain=None):
    """A one page county bulletin an officer can open, print or forward."""
    t = table[table["admin2"] == county]
    worst = max(t["phase"], key=["Normal", "Stress", "Alert", "Crisis"].index) if len(t) else "No data"
    n_warn = int((t["p_any"] >= thr).sum()) if thr is not None and "p_any" in t else 0
    colour = {"Normal": "#2e7d32", "Stress": "#f9a825", "Alert": "#ef6c00", "Crisis": "#c62828"}.get(worst, "#757575")
    rows = "".join(
        f"<tr><td>{html.escape(r.market)}</td><td>{r.crop}</td><td>{r.pricetype}</td>"
        f"<td>{r.price:.0f}</td><td>{r.gap:+.0f}%</td><td><b>{r.phase}</b></td>"
        f"<td>{outlook(getattr(r, 'p_any', None), thr)}</td><td>{html.escape(r.main_reason)}</td>"
        f"<td>{html.escape(action(r.phase, getattr(r, 'p_any', None), thr))}</td></tr>"
        for r in t.itertuples())
    rain_line = f"<p>Rainfall over the last 3 months: <b>{rain:.0f}% of normal</b>{' (dry spell)' if rain < 75 else ''}.</p>" if rain is not None else ""
    return f"""<!doctype html><html><head><meta charset="utf-8"><title>SokoRadar bulletin {html.escape(county)} {month}</title>
<style>body{{font-family:Arial,sans-serif;margin:32px;color:#222}} h1{{margin:0}} .badge{{display:inline-block;padding:6px 14px;
border-radius:6px;color:#fff;background:{colour};font-weight:bold}} table{{border-collapse:collapse;width:100%;font-size:13px;margin-top:12px}}
th,td{{border:1px solid #ddd;padding:6px;text-align:left;vertical-align:top}} th{{background:#f4f4f4}} .note{{color:#666;font-size:12px}}</style></head>
<body><h1>SokoRadar county bulletin</h1><h2>{html.escape(county)} County, {month.strftime('%B %Y')}</h2>
<p>Overall status: <span class="badge">{worst}</span> &nbsp; Markets with a high chance of Alert in the next 3 months: <b>{n_warn}</b></p>
{rain_line}<p><b>Suggested action:</b> {html.escape(action(worst))}</p>
<table><tr><th>Market</th><th>Crop</th><th>Type</th><th>KES/kg</th><th>vs normal</th><th>Phase</th><th>Next 3 months</th><th>Main reason</th><th>Suggested action</th></tr>{rows}</table>
<p class="note">Phases follow WFP's ALPS method: each price is compared with its normal level for the time of year, learned from earlier months only.
The 3 month outlook comes from the SokoRadar early warning model. Real WFP market prices only. Price alerts are one input to NDMA drought phase
decisions, alongside other indicators. Sources: WFP via HDX, CHIRPS. Group 10, Moringa School.</p></body></html>"""

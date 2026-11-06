"""Tables the pages share: the ranked market list and the county summary for a month."""
import pandas as pd
import streamlit as st

from src.actions import action, outlook
from src.alerts import PHASES, detail, reasons, worst_phase
from src.loaders import KEYS, ew_threshold, get_alps, get_counties, get_ew, get_prices, rain_for


@st.cache_data
def market_table(month_str, crop):
    """Every market reporting in a month: price, normal level, phase, chance of Alert in the
    next 3 months, main reason and suggested action. Highest priority first."""
    month = pd.Period(month_str, freq="M")
    ca, prices, thr = get_alps(), get_prices(), ew_threshold()
    rows = ca[ca["month"] == month]
    if crop != "All crops":
        rows = rows[rows["crop"] == crop]
    out = []
    for r in rows.itertuples():
        key = tuple(getattr(r, k) for k in KEYS)
        d = detail(prices[key], month) if key in prices else None
        if d is None:
            continue
        rain = rain_for(r.pcode, month)
        out.append({**dict(zip(KEYS, key)), "pcode": r.pcode, "asal": r.asal, **d, "rain": rain,
                    "main_reason": reasons(d, r.crop, month, rain)[0]})
    df = pd.DataFrame(out)
    if df.empty:
        return df
    ew = get_ew()
    if ew is not None:
        df = df.merge(ew.loc[ew["month"] == month, KEYS + ["p_any"]], on=KEYS, how="left")
    else:
        df["p_any"] = float("nan")
    df["outlook"] = [outlook(p, thr) for p in df["p_any"]]
    df["action"] = [action(ph, p, thr) for ph, p in zip(df["phase"], df["p_any"])]
    df["rank"] = df["phase"].map({p: i for i, p in enumerate(PHASES)})
    return df.sort_values(["rank", "p_any", "score"], ascending=False, na_position="last").reset_index(drop=True)


def county_status(month, crop, mode="now"):
    """One row per county for the map. mode 'now' = worst phase this month,
    'warn' = markets with a high chance of Alert in the next 3 months."""
    t = market_table(str(month), crop)
    cty = get_counties()
    if t.empty:
        return pd.DataFrame(columns=["county", "pcode", "phase", "detail"])
    thr = ew_threshold()
    t = t.assign(hot=t["phase"].isin(["Alert", "Crisis"]),
                 warn=(t["p_any"] >= thr) if thr is not None else False)
    g = t.groupby(["admin2", "pcode"], dropna=False).agg(
        phase=("phase", worst_phase), markets=("market", "size"), hot=("hot", "sum"), warn=("warn", "sum")).reset_index()
    g["county"] = g["admin2"]
    if mode == "warn":
        g["phase"] =["Early warning" if w > 0 else "No warning" for w in g["warn"]]
        g["detail"] = g["warn"].astype(int).astype(str) + " of " + g["markets"].astype(str) + " price series likely to hit Alert in 3 months"
    else:
        g["detail"] = g["hot"].astype(int).astype(str) + " of " + g["markets"].astype(str) + " price series in Alert or Crisis"
    if cty is not None:   # show counties with no market data in grey
        rest = cty[~cty["pcode"].isin(g["pcode"])].assign(phase="No data", detail="No real market prices")
        g = pd.concat([g, rest[["county", "pcode", "phase", "detail"]]], ignore_index=True)
    return g


def phase_share(crop="All crops", by="crop"):
    """Share of markets in Alert or Crisis per month (3 month average), one column per group."""
    ca = get_alps()
    if crop != "All crops":
        ca = ca[ca["crop"] == crop]
    hit = ca.assign(hit=ca["phase"].isin(["Alert", "Crisis"]))
    s = hit.groupby(["month", by])["hit"].mean().unstack() if by else hit.groupby("month")["hit"].mean().to_frame("In Alert or Crisis")
    return s.rolling(3, min_periods=1).mean()


def warning_share(crop="All crops"):
    """Share of markets in Alert or Crisis now, next to the share SokoRadar warned about."""
    ew, thr = get_ew(), ew_threshold()
    if ew is None:
        return None
    if crop != "All crops":
        ew = ew[ew["crop"] == crop]
    ew = ew[ew["p_any"].notna()]
    s = pd.DataFrame({"In Alert or Crisis": ew.assign(h=ew["alps"] >= 1).groupby("month")["h"].mean(),
                      "Warned by SokoRadar (next 3 months)": ew.assign(w=ew["p_any"] >= thr).groupby("month")["w"].mean()})
    return s.rolling(3, min_periods=1).mean()

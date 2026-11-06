"""Alert logic: ALPS phases, the normal price line, plain reasons and the rainfall what-if."""
import numpy as np
import pandas as pd

PHASES = ["Normal", "Stress", "Alert", "Crisis"]
COLOURS = {"Normal": "#2e7d32", "Stress": "#f9a825", "Alert": "#ef6c00", "Crisis": "#c62828", "No data": "#bdbdbd"}
CUTS = [-np.inf, 0.25, 1, 2, np.inf]          # WFP ALPS: Stress from 0.25, Alert from 1, Crisis from 2
LEAN_MONTHS = {"Maize": (5, 6, 7)}            # from the EDA: maize is dearest in May to July


def to_phase(score):
    if np.isscalar(score):
        return "No data" if pd.isna(score) else PHASES[int(np.searchsorted(CUTS[1:-1], score, side="right"))]
    return pd.cut(score, CUTS, right=False, labels=PHASES)


def worst_phase(phases):
    p = [x for x in phases if x in PHASES]
    return max(p, key=PHASES.index) if p else "No data"


def _design(index):
    t = np.arange(len(index))
    m = index.month
    return np.column_stack([np.ones(len(index)), t] + [(m == k).astype(float) for k in range(2, 13)])


def fit_at(price, i, X=None, min_obs=36):
    """Expected (normal) price and ALPS score for month i, learned from earlier months only."""
    X = _design(price.index) if X is None else X
    past = np.where(price.notna().values[:i])[0]
    if len(past) < min_obs or pd.isna(price.iloc[i]):
        return np.nan, np.nan
    beta, *_ = np.linalg.lstsq(X[past], price.values[past], rcond=None)
    sd = (price.values[past] - X[past] @ beta).std(ddof=X.shape[1])
    exp = float(X[i] @ beta)
    return exp, (price.iloc[i] - exp) / sd


def normal_line(price):
    X = _design(price.index)
    res = [fit_at(price, i, X) for i in range(len(price))]
    exp = pd.Series([r[0] for r in res], index=price.index)
    score = pd.Series([r[1] for r in res], index=price.index)
    return exp, score


def detail(price, month):
    """Everything the pages need to describe one market in one month."""
    if month not in price.index:
        return None
    i = price.index.get_loc(month)
    exp, score = fit_at(price, i)
    prev = price.iloc[i - 3] if i >= 3 else np.nan
    return {
        "price": float(price.iloc[i]),
        "normal": exp,
        "gap": 100 * (price.iloc[i] / exp - 1) if pd.notna(exp) else np.nan,
        "chg3": 100 * (price.iloc[i] / prev - 1) if pd.notna(prev) else np.nan,
        "score": score,
        "phase": to_phase(score),
    }


def reasons(d, crop, month, rain=None):
    """Plain sentences, most important first. Rule based until the model's SHAP drivers are connected."""
    out = []
    if rain is not None and rain < 75:
        out.append(f"Rains were only {rain:.0f}% of normal over the last 3 months (dry spell).")
    if pd.notna(d["chg3"]) and d["chg3"] >= 10:
        out.append(f"The price rose {d['chg3']:.0f}% over the last 3 months.")
    if month.month in LEAN_MONTHS.get(crop, ()):
        out.append(f"{month.strftime('%B')} is the lean season before the harvest, when {crop.lower()} is usually dearer.")
    if pd.notna(d["gap"]):
        word = "above" if d["gap"] >= 0 else "below"
        out.append(f"The price is {abs(d['gap']):.0f}% {word} its normal level for {month.strftime('%B')}.")
    if rain is not None and rain >= 75:
        out.append(f"Rains were {rain:.0f}% of normal over the last 3 months.")
    if d["phase"] not in ("Alert", "Crisis") and pd.notna(d["gap"]):
        # no alert: lead with where the price stands, not with a warning sign
        gap_line = out.pop(-2 if rain is not None and rain >= 75 else -1)
        out.insert(0, gap_line)
    return out or ["Not enough history to explain this month yet."]


def rainfall_what_if(price, rain, level, band=15):
    """Average 3 month price change after months with rainfall near `level` % of normal,
    compared with all months. Uses this market's own history."""
    fwd = 100 * (price.shift(-3) / price - 1)
    df = pd.DataFrame({"fwd": fwd, "rain": rain.reindex(price.index)}).dropna()
    if len(df) < 12:
        return None
    near = df[(df["rain"] - level).abs() <= band]
    return {"near": near["fwd"].mean() if len(near) else np.nan, "n": len(near), "all": df["fwd"].mean(), "n_all": len(df)}

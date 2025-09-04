# blocks/components/gee/nightlights_break_detection.py
"""
Purpose
-------
Struktureller Trendbruch in einer Monats-Zeitreihe 'mean_rad' via BIC-Vergleich:
- Modell 1: eine lineare Regression
- Modell 2: piecewise-linear mit einer Break-Position k
- ΔBIC = BIC(piecewise) - BIC(linear). Break, wenn ΔBIC <= bic_threshold.

Contract
--------
def find_trend_break(
    df, date_col="date", value_col="mean_rad",
    min_segment=6, bic_threshold=-10,
    pre_window=6, post_window=12, min_gap_post=1
) -> dict

Args
----
df : pandas.DataFrame mit Spalten [date_col, value_col]
min_segment : int   Mindestens so viele Monate je Seite
bic_threshold : float  ΔBIC-Schwelle (<= → Break)
pre_window, post_window, min_gap_post : Heuristiken zur repräsentativen Bildwahl

Returns
-------
dict mit Feldern:
  has_break: bool
  delta_bic: float
  break_date: pandas.Timestamp | None
  pre_image_date: pandas.Timestamp | None
  post_image_date: pandas.Timestamp | None
  pre_mean, post_mean: float | optional

Side-effects
------------
Keine Streamlit-Ausgaben.
"""
from __future__ import annotations
import numpy as np
import pandas as pd

def find_trend_break(
    df,
    date_col: str = "date",
    value_col: str = "mean_rad",
    min_segment: int = 6,
    bic_threshold: float = -10,
    pre_window: int = 6,
    post_window: int = 12,
    min_gap_post: int = 1,
):
    x = df[[date_col, value_col]].dropna().copy()
    x[date_col] = pd.to_datetime(x[date_col])
    x = x.sort_values(date_col).reset_index(drop=True)

    y = x[value_col].astype(float).to_numpy()
    n = len(y)
    if n < 2 * min_segment + 1:
        raise ValueError(f"Need at least {2*min_segment+1} rows, got {n}.")
    t = np.arange(n, dtype=float)

    # Single linear model
    X1 = np.column_stack([np.ones(n), t])
    b1, *_ = np.linalg.lstsq(X1, y, rcond=None)
    sse1 = np.sum((y - X1 @ b1) ** 2)
    bic1 = n * np.log(sse1 / n) + X1.shape[1] * np.log(n)

    # Best piecewise-linear split
    best_bic, best_k = np.inf, None
    for k in range(min_segment, n - min_segment):
        I = (np.arange(n) >= k).astype(float)
        dt = (t - t[k]) * I
        Xk = np.column_stack([np.ones(n), t, I, dt])
        bk, *_ = np.linalg.lstsq(Xk, y, rcond=None)
        ssek = np.sum((y - Xk @ bk) ** 2)
        bick = n * np.log(ssek / n) + Xk.shape[1] * np.log(n)
        if bick < best_bic:
            best_bic, best_k = bick, k

    delta_bic = best_bic - bic1
    has_break = bool(delta_bic <= bic_threshold)
    if not has_break:
        return {
            "has_break": False,
            "delta_bic": float(delta_bic),
            "break_date": None,
            "pre_image_date": None,
            "post_image_date": None,
        }

    k = int(best_k)
    pre = y[:k]
    post = y[k:]
    pre_mean, post_mean = float(pre.mean()), float(post.mean())

    # Repräsentative Monate um die Mittelwerte
    pre_lo = max(0, k - pre_window - 1)
    pre_hi = max(pre_lo, k - 1)  # exclude k-1
    pre_candidates = np.arange(pre_lo, pre_hi) if pre_hi > pre_lo else np.arange(0, k)
    pre_idx = int(pre_candidates[np.argmin(np.abs(y[pre_candidates] - pre_mean))])

    post_start = min(k + max(1, min_gap_post), n - 1)
    post_end = min(k + post_window, n - 1)
    post_candidates = np.arange(post_start, post_end + 1) if post_end >= post_start else np.arange(k, n)
    post_idx = int(post_candidates[np.argmin(np.abs(y[post_candidates] - post_mean))])

    break_date = pd.to_datetime(x.loc[k, date_col])
    pre_img = pd.to_datetime(x.loc[pre_idx, date_col])
    post_img = pd.to_datetime(x.loc[post_idx, date_col])

    return {
        "has_break": True,
        "delta_bic": float(delta_bic),
        "break_date": break_date,
        "pre_image_date": pre_img,
        "post_image_date": post_img,
        "pre_mean": pre_mean,
        "post_mean": post_mean,
    }

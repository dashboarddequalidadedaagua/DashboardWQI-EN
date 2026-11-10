"""
Error metrics of the predictions against the observed WQI (pure functions,
no Streamlit, testable on their own).

y = observed WQI; p = prediction exactly as exported (LR already rounded
with np.round; Decision Tree as it comes out of the model). A value that
cannot be calculated is returned as None and shown as "N/A".
"""

import math
import re
from decimal import ROUND_HALF_UP, Decimal

import numpy as np
import pandas as pd

import config


def compute_metrics(y, p):
    """R2, MAE, RMSE and MAPE (%) of one model.

    R2 follows the sklearn definition (r2_score): 1 - SS_res / SS_tot, it can
    be negative. MAPE excludes the rows with y = 0; the excluded positions
    are returned in 'zero_indices' to be listed in Warnings.
    """
    y = np.asarray(y, dtype=float)
    p = np.asarray(p, dtype=float)
    error = y - p

    ss_res = float(np.sum(error ** 2))
    ss_tot = float(np.sum((y - y.mean()) ** 2))
    r2 = 1 - ss_res / ss_tot if ss_tot > 0 else None

    mae = float(np.mean(np.abs(error)))
    rmse = float(np.sqrt(np.mean(error ** 2)))

    non_zero = y != 0
    if non_zero.any():
        mape = float(100 * np.mean(np.abs(error[non_zero]) / np.abs(y[non_zero])))
    else:
        mape = None

    return {
        'R2': r2,
        'MAE': mae,
        'RMSE': rmse,
        'MAPE': mape,
        'zero_indices': np.flatnonzero(~non_zero).tolist(),
    }


def error_band_percentages(y, p):
    """% of the samples in each absolute error band |y - p| (config.ERROR_BANDS).

    The upper limit belongs to the band. The bands add up to 100%. With no
    samples, returns None.
    """
    y = np.asarray(y, dtype=float)
    p = np.asarray(p, dtype=float)
    if len(y) == 0:
        return None
    error = np.abs(y - p)
    percentages = []
    for _, _, lo, hi in config.ERROR_BANDS:
        inside = error >= 0 if lo is None else error > lo
        if hi is not None:
            inside = inside & (error <= hi)
        percentages.append(float(100 * np.mean(inside)))
    return percentages


def wqi_category(value):
    """CETESB category of a WQI value (config.WQI_CATEGORIES). The upper limit
    belongs to the category; below 0 is Very poor, above 100 is Excellent."""
    for name, _, hi, _, _ in config.WQI_CATEGORIES:
        if value <= hi:
            return name
    return config.WQI_CATEGORIES[-1][0]


def classify_monitoring(y):
    """Samples of the monitoring chart below and above the thresholds.

    Same rule as the CETESB categories (the upper limit belongs to the
    category): poor or very poor = WQI up to the lower threshold (inclusive);
    excellent = WQI above the upper threshold (exactly the upper threshold is
    Good). Compares the full value, without rounding.
    Returns (low, high), two boolean arrays of the same size as y.
    """
    y = np.asarray(y, dtype=float)
    return y <= config.MONITORING_LOWER_THRESHOLD, y > config.MONITORING_UPPER_THRESHOLD


# ---------------------------------------------------------------------------
# Sampling Sites
# ---------------------------------------------------------------------------
def normalize_site(value):
    """Value of the Sampling Site column as text. The group is the value as
    the user typed it (case, accents and inner spaces are not changed).

    An empty cell or a cell with only spaces returns None. An integer coming
    from Excel as 5.0 returns '5'.
    """
    if value is None or value is pd.NA or value is pd.NaT:
        return None
    if isinstance(value, bool):
        return str(value)
    if isinstance(value, (float, np.floating)):
        if math.isnan(value):
            return None
        if float(value).is_integer():
            return str(int(value))
    elif isinstance(value, (int, np.integer)):
        return str(int(value))
    text = str(value).strip()
    return text or None


def _natural_key(text):
    """Numbers inside the text compared as numbers ('2 X' before '10 X')."""
    parts = re.split(r'(\d+)', text)
    return tuple(int(p) if i % 2 else p.casefold() for i, p in enumerate(parts))


def sort_sites(sites):
    """Distinct sampling sites (without the empty ones) in screen order:
    1st number of rows (descending), 2nd natural order, 3rd order of
    appearance. Receives the values already normalized (normalize_site)."""
    count = {}
    for s in sites:
        if s is not None:
            count[s] = count.get(s, 0) + 1
    # sorted is stable: on a complete tie the order of appearance is kept
    return sorted(count, key=lambda s: (-count[s], _natural_key(s)))


def site_table(sites, y, p_lr, p_dt):
    """Metrics per sampling site (R2, MAE, MAPE, RMSE of both models).

    Receives only the rows after the filter with a valid observed WQI, with
    the site already normalized (None = empty, left out). Returns a list of
    dicts with 'site', 'n' (rows of the site used in the calculation),
    'sufficient' and 'lr'/'dt' (dict of metrics or None), in the order of
    sort_sites.
    """
    sites = list(sites)
    y = np.asarray(y, dtype=float)
    p_lr = np.asarray(p_lr, dtype=float)
    p_dt = np.asarray(p_dt, dtype=float)

    table = []
    for site in sort_sites(sites):
        idx = np.asarray([i for i, s in enumerate(sites) if s == site])
        sufficient = len(idx) >= config.MIN_ROWS_PER_SITE
        lr = dt = None
        if sufficient:
            lr = compute_metrics(y[idx], p_lr[idx])
            dt = compute_metrics(y[idx], p_dt[idx])
        table.append({'site': site, 'n': len(idx), 'sufficient': sufficient,
                      'lr': lr, 'dt': dt})
    return table


# ---------------------------------------------------------------------------
# Formatting for the screen (display only; calculations and Excel use the
# full value)
# ---------------------------------------------------------------------------
def round_half_up(value, decimals):
    """Rounds to the nearest; on an exact tie, away from zero (like Excel's
    ROUND). Returns a Decimal, without sign when it is zero.
    None, NaN and infinity return None."""
    if value is None:
        return None
    value = float(value)
    if not math.isfinite(value):
        return None
    d = Decimal(str(value)).quantize(Decimal(1).scaleb(-decimals), rounding=ROUND_HALF_UP)
    return d.copy_abs() if d == 0 else d


def format_number(value, decimals=config.DECIMALS_WQI, suffix=''):
    """1234.56 -> '1,234.6' (decimals=1); None -> 'N/A'. Never '-0.0'."""
    d = round_half_up(value, decimals)
    if d is None:
        return config.NOT_APPLICABLE
    return f"{d:,.{decimals}f}" + suffix


def better_model(value_lr, value_dt, decimals, direction):
    """'lr', 'dt' or None, comparing the values already rounded as displayed.

    direction: 'higher' (R2) or 'lower' (errors). Tie or None value: None.
    """
    a, b = round_half_up(value_lr, decimals), round_half_up(value_dt, decimals)
    if a is None or b is None or a == b:
        return None
    if direction == 'higher':
        return 'lr' if a > b else 'dt'
    return 'lr' if a < b else 'dt'


def format_pair(value_lr, value_dt, decimals=config.DECIMALS_WQI, suffix='', highlight=None):
    """'LR = 0.89 | DT = 0.91' (MAPE with suffix '%').

    highlight: 'lr' or 'dt' wraps the part of that model in config.HIGHLIGHT_FORMAT.
    """
    part_lr, part_dt = config.PAIR_FORMAT.split(config.PAIR_SEPARATOR)
    part_lr = part_lr.format(lr=format_number(value_lr, decimals, suffix))
    part_dt = part_dt.format(dt=format_number(value_dt, decimals, suffix))
    if highlight == 'lr':
        part_lr = config.HIGHLIGHT_FORMAT.format(text=part_lr)
    elif highlight == 'dt':
        part_dt = config.HIGHLIGHT_FORMAT.format(text=part_dt)
    return config.PAIR_SEPARATOR.join([part_lr, part_dt])

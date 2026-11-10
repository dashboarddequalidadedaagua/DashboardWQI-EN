"""
Reading of the spreadsheet, the original training prediction pipeline and building of
the Excel files (no Streamlit, testable on their own).

The pipeline (filter, removal of TON and WQI before the model, imputer,
winsorization, scaler, models, np.round of the LR, VARIABLE_ORDER) is the
same as in training. The objects loaded with joblib.load() are ALWAYS used
with .transform()/.predict(), never with the fitting method.

The columns use the internal abbreviations everywhere (the scaler and the
imputer store these names). There is no translation layer: the accepted
headers, the screen, the Excel files and the warnings use the same
abbreviations (only PH is shown as pH, see config.DISPLAY_NAMES).
"""

import csv
import io
import os
import re
from datetime import date, datetime, timezone

import joblib
import numpy as np
import pandas as pd
from scipy.stats.mstats import winsorize

import config
import metrics

FOLDER = os.path.dirname(os.path.abspath(__file__))


class ReadError(Exception):
    pass


def display_name(internal):
    """Abbreviation shown to the user (PH -> pH); all others stay the same."""
    return config.DISPLAY_NAMES.get(internal, internal)


# ---------------------------------------------------------------------------
# Models
# ---------------------------------------------------------------------------
def load_models(folder=FOLDER):
    files = config.MODEL_FILES
    lr = joblib.load(os.path.join(folder, files['lr']))
    dt = joblib.load(os.path.join(folder, files['dt']))
    scaler = joblib.load(os.path.join(folder, files['scaler']))
    imputer = joblib.load(os.path.join(folder, files['imputer']))
    return lr, dt, scaler, imputer


def model_details(lr, dt, imputer):
    """Numbers of the model details read from the loaded objects."""
    return {
        'n_variables': int(lr.n_features_in_),
        'depth': int(dt.get_depth()),
        'leaves': int(dt.get_n_leaves()),
        'neighbors': int(imputer.n_neighbors),
    }


# ---------------------------------------------------------------------------
# Reading
# ---------------------------------------------------------------------------
def read_spreadsheet(name, data):
    """Reads .xlsx, .xls or .csv from the bytes of the file."""
    ext = os.path.splitext(name)[1].lower().lstrip('.')
    if ext not in config.ACCEPTED_FORMATS:
        raise ReadError(name)
    try:
        if ext == 'xlsx':
            return pd.read_excel(io.BytesIO(data), engine='openpyxl')
        if ext == 'xls':
            return pd.read_excel(io.BytesIO(data), engine='xlrd')
        return _read_csv(data)
    except Exception as e:  # corrupted file, wrong format etc.
        raise ReadError(str(e)) from e


def _read_csv(data):
    for encoding in ('utf-8-sig', 'latin-1'):
        try:
            text = data.decode(encoding)
            break
        except UnicodeDecodeError:
            continue
    sample = text[:5000]
    try:
        sep = csv.Sniffer().sniff(sample, delimiters=';,\t').delimiter
    except csv.Error:
        sep = ','
    # the decimal separator is always the period, whatever the column separator
    return pd.read_csv(io.StringIO(text), sep=sep, decimal='.')


_UNIT_PATTERN = re.compile(r'^\s*([A-Za-z]+)\s*[\(\[]\s*(.*?)\s*[\)\]]\s*$')
_INTERNAL_ABBREVIATIONS = config.VARIABLE_ORDER + [config.TON_COLUMN, config.WQI_COLUMN]
# header (upper case) -> internal abbreviation
_ACCEPTED_ABBREVIATIONS = {s.upper(): s for s in _INTERNAL_ABBREVIATIONS}
# expected unit of each internal abbreviation (wrong unit message)
_EXPECTED_UNIT = {s: u for s, _, u in config.VARIABLE_DICTIONARY}
for _col, _, _u, _, _ in config.TEMPLATE_OPTIONAL_COLUMNS:
    if _col in _INTERNAL_ABBREVIATIONS:
        _EXPECTED_UNIT[_col] = _u


def _normalize_unit(text):
    return re.sub(r'\s+', '', str(text)).lower()


def normalize_columns(df):
    """Standardizes the column names to the internal abbreviations.

    Accepts the abbreviation (e.g. BOD) with any combination of upper and
    lower case and, optionally, the unit in the header (e.g. "BOD (mg/L)").
    A unit different from the accepted forms generates a block. The same
    variable in two columns: the first one is used, the other is discarded
    and goes to Warnings. The date column becomes "Date". Sampling Site: the
    name with the highest priority in ACCEPTED_SITE_NAMES is used.

    Returns (df, blocks, warnings).
    """
    rename = {}
    discard = []
    blocks = []
    warnings = []
    used = {}              # internal abbreviation -> name of the column used
    has_date = False
    site_candidates = []   # (priority, column)
    for col in df.columns:
        name = str(col).strip()
        text, unit = name, None
        m = _UNIT_PATTERN.match(name)
        if m and m.group(1).upper() in _ACCEPTED_ABBREVIATIONS:
            text, unit = m.group(1), m.group(2)
        target = _ACCEPTED_ABBREVIATIONS.get(text.upper())
        if target is not None:
            if target in used:
                warnings.append((config.WARNING_DUPLICATE_COLUMN.format(
                    abbreviation=display_name(target), col1=used[target], col2=name), 0, ''))
                discard.append(col)
                continue
            if unit is not None and target in config.ACCEPTED_UNITS:
                if _normalize_unit(unit) not in config.ACCEPTED_UNITS[target]:
                    blocks.append(config.BLOCK_UNIT.format(
                        column=display_name(target), unit=unit, expected=_EXPECTED_UNIT[target]))
            used[target] = name
            rename[col] = target
        elif name.lower() in config.ACCEPTED_DATE_NAMES and not has_date:
            rename[col] = config.DATE_COLUMN
            has_date = True
        elif name.lower() in config.ACCEPTED_SITE_NAMES:
            site_candidates.append((config.ACCEPTED_SITE_NAMES.index(name.lower()), col))
    if site_candidates:
        rename[min(site_candidates, key=lambda c: c[0])[1]] = config.SITE_COLUMN
    # an unused column with the same name as a standardized column is dropped
    # (avoids two columns with the same name)
    targets = set(rename.values())
    discard += [c for c in df.columns if c not in rename and str(c).strip() in targets]
    df = df.drop(columns=discard).rename(columns=rename)
    return df, blocks, warnings


def _to_number(series):
    """Converts to number; text becomes empty. Returns (series, text_mask).

    The period is the decimal separator. Text with a comma (e.g. "2,5" or
    "24,000") is not converted: it becomes an empty cell and is counted as
    text instead of a number.
    """
    if pd.api.types.is_numeric_dtype(series):
        return series, pd.Series(False, index=series.index)
    text = series.astype('string').str.strip()
    empty = series.isna() | (text == '')
    converted = pd.to_numeric(text, errors='coerce')
    text_mask = converted.isna() & ~empty
    return converted.astype(float), text_mask.fillna(False).astype(bool)


def _parse_one_date(value):
    """One cell of the date column -> Timestamp or NaT (date that could not be read)."""
    if isinstance(value, (datetime, date, np.datetime64, pd.Timestamp)):
        return pd.Timestamp(value)
    if isinstance(value, str):
        text = value.strip()
        for fmt in config.DATE_TEXT_FORMATS:
            try:
                return pd.Timestamp(datetime.strptime(text, fmt))
            except ValueError:
                continue
    return pd.NaT


def parse_dates(series):
    """Date column -> datetime series.

    A column that is already a date column (Excel/pandas) is used as it is.
    Otherwise each value is read individually: a value that is already a date
    is used as it is; a text is tried with the formats of
    config.DATE_TEXT_FORMATS, in order. Anything else becomes NaT.
    """
    if pd.api.types.is_datetime64_any_dtype(series):
        return series
    values = [_parse_one_date(v) for v in series]
    return pd.Series(pd.DatetimeIndex(values), index=series.index)


def _row_list(rows):
    text = config.LIST_SEPARATOR.join(str(int(x)) for x in rows)
    return text if len(text) < 32000 else text[:32000] + config.ROW_LIST_TRUNCATION


def _missing_list(internal_abbreviations):
    """'BOD, THC' (abbreviations as displayed)."""
    return config.LIST_SEPARATOR.join(display_name(s) for s in internal_abbreviations)


# ---------------------------------------------------------------------------
# Full processing
# ---------------------------------------------------------------------------
def process(name, data, models):
    """Reads the file, runs the pipeline and calculates everything the screen
    and the Excel file use.

    Returns a dict (serializable, for the Streamlit cache).
    """
    r = {
        'file_name': name,
        'read': False,
        'blocks': [],
        'warnings': [],
        'rows_read': 0,
        'rows_removed': 0,
        'removed': None,
        'res': None,
        'adjustments': None,
        'has_date': False,
        'has_site_column': False,
        'has_sites': False,
        'n_wqi_valid': 0,
        'metrics': None,
        'sites': None,
        'medians': None,
        'error_bands': None,
    }

    try:
        df = read_spreadsheet(name, data)
    except ReadError:
        r['blocks'].append(config.BLOCK_READ)
        return r
    r['read'] = True

    for col in config.JUNK_INDEX_COLUMNS:
        if col in df.columns:
            df = df.drop(columns=[col])
    df = df.reset_index(drop=True)
    r['rows_read'] = len(df)
    if len(df) == 0:
        r['blocks'].append(config.BLOCK_EMPTY)
        return r

    df, unit_blocks, column_warnings = normalize_columns(df)
    r['warnings'] += column_warnings
    missing = [c for c in config.VARIABLE_ORDER if c not in df.columns]
    if missing:
        r['blocks'].append(config.BLOCK_COLUMNS.format(columns=_missing_list(missing)))
    r['blocks'] += unit_blocks
    if r['blocks']:
        return r

    raw = df.copy()
    original_row = pd.Series(df.index + 2, index=df.index)  # row 1 = header
    warnings = r['warnings']

    # numbers (text instead of a number becomes an empty cell)
    for col in config.VARIABLE_ORDER + [config.TON_COLUMN, config.WQI_COLUMN]:
        if col in df.columns:
            df[col], text = _to_number(df[col])
            if text.any():
                warnings.append((config.WARNING_NON_NUMERIC.format(n=int(text.sum()),
                                                                   column=display_name(col)),
                                 int(text.sum()), _row_list(original_row[text])))

    # date (does not go into the model)
    dates = None
    if config.DATE_COLUMN in df.columns:
        dates = parse_dates(df[config.DATE_COLUMN])
        df = df.drop(columns=[config.DATE_COLUMN])

    # filter of values outside the range used to train the models (same as in training)
    conditions = {}
    for var, (minimum, maximum) in config.FILTER_LIMITS.items():
        if var not in df.columns:
            continue
        if minimum is not None:
            conditions[(var, 'below', minimum)] = df[var] < minimum
        if maximum is not None:
            conditions[(var, 'above', maximum)] = df[var] > maximum
    mask_out_of_range = pd.Series(False, index=df.index)
    for cond in conditions.values():
        mask_out_of_range = mask_out_of_range | cond

    reasons = []
    for i in df.index[mask_out_of_range]:
        parts = []
        for (var, side, limit), cond in conditions.items():
            if cond[i]:
                template = config.REASON_ABOVE if side == 'above' else config.REASON_BELOW
                parts.append(template.format(var=display_name(var), maximum=limit, minimum=limit))
        reasons.append(config.REASON_SEPARATOR.join(parts))
    removed = raw[mask_out_of_range].copy()
    removed.insert(0, config.EXCEL_COLUMN_REASON, reasons, allow_duplicates=True)
    removed.insert(0, config.EXCEL_COLUMN_ROW, original_row[mask_out_of_range].values,
                   allow_duplicates=True)
    # headers with the abbreviations as displayed (PH -> pH)
    removed = removed.rename(columns={s: display_name(s) for s in _INTERNAL_ABBREVIATIONS})
    r['removed'] = removed.reset_index(drop=True)
    r['rows_removed'] = int(mask_out_of_range.sum())

    pct = 100 * r['rows_removed'] / r['rows_read']
    if pct > config.HIGH_REMOVAL_ALERT_PCT:
        warnings.append((config.WARNING_HIGH_REMOVAL, r['rows_removed'], ''))

    df_filtered = df[~mask_out_of_range].copy()
    if len(df_filtered) == 0:
        r['blocks'].append(config.BLOCK_ALL_REMOVED)
        return r

    # observed WQI kept before removing the column from the model's X
    if config.WQI_COLUMN in df_filtered.columns:
        wqi_observed = df_filtered[config.WQI_COLUMN].astype(float)
    else:
        wqi_observed = pd.Series(np.nan, index=df_filtered.index)

    # -----------------------------------------------------------------------
    # ORIGINAL TRAINING PIPELINE (do not change): removes TON and WQI, fixed order of
    # the variables, imputer.transform, winsorization, scaler.transform, predict.
    # -----------------------------------------------------------------------
    lr, dt, scaler, imputer = models
    X_raw = df_filtered.drop(columns=config.COLUMNS_DROPPED_BEFORE_MODEL, errors='ignore')
    X_raw = X_raw[config.VARIABLE_ORDER]

    X_imputed = pd.DataFrame(
        imputer.transform(X_raw),
        columns=X_raw.columns,
        index=X_raw.index
    )
    X = X_imputed.copy()
    for c in config.WINSORIZE_COLUMNS:
        X[c] = winsorize(X[c], limits=config.WINSORIZE_LIMITS)

    X_scaled = scaler.transform(X)

    pred_lr = np.round(lr.predict(X_scaled))
    pred_dt = dt.predict(X_scaled)
    # -----------------------------------------------------------------------

    row_filtered = original_row[df_filtered.index]

    # automatic adjustments (cells filled and extreme values adjusted)
    adjustments = []
    empty = X_raw.isna()
    for c in config.VARIABLE_ORDER:
        for i in X_raw.index[empty[c]]:
            adjustments.append((row_filtered[i], display_name(c), config.ADJUSTMENT_IMPUTATION,
                                None, X_imputed.at[i, c]))
        changed = X_imputed[c].values != X[c].values
        for i in X.index[changed]:
            adjustments.append((row_filtered[i], display_name(c), config.ADJUSTMENT_WINSORIZATION,
                                X_imputed.at[i, c], X.at[i, c]))
    adjustments_df = pd.DataFrame(adjustments, columns=config.EXCEL_ADJUSTMENTS_COLUMNS)
    r['adjustments'] = adjustments_df.sort_values(config.EXCEL_ADJUSTMENTS_COLUMNS[:2],
                                                  kind='stable').reset_index(drop=True)
    r['cells_imputed'] = int(empty.values.sum())
    r['values_winsorized'] = int(
        (adjustments_df[config.EXCEL_COLUMN_ADJUSTMENT] == config.ADJUSTMENT_WINSORIZATION).sum())

    # predictions table
    res = pd.DataFrame({'Original_row': row_filtered.values})
    if dates is not None:
        res[config.DATE_COLUMN] = dates[df_filtered.index].values
        invalid_dates = res[config.DATE_COLUMN].isna()
        if invalid_dates.any():
            warnings.append((config.WARNING_INVALID_DATE.format(n=int(invalid_dates.sum())),
                             int(invalid_dates.sum()),
                             _row_list(res['Original_row'][invalid_dates])))
        r['has_date'] = True
    else:
        warnings.append((config.WARNING_NO_DATE, 0, ''))
    if config.SITE_COLUMN in df.columns:
        r['has_site_column'] = True
        sites = [metrics.normalize_site(v) for v in raw.loc[df_filtered.index, config.SITE_COLUMN]]
        res[config.SITE_COLUMN] = pd.Series(sites, dtype=object)
        empty_site = res[config.SITE_COLUMN].isna()
        if empty_site.any():
            warnings.append((config.WARNING_EMPTY_SITE.format(n=int(empty_site.sum())),
                             int(empty_site.sum()), _row_list(res['Original_row'][empty_site])))
    res['WQI_observed'] = wqi_observed.values
    res['Prediction_LR'] = pred_lr
    res['Prediction_DT'] = pred_dt
    for c in config.VARIABLE_ORDER:
        res[c] = X[c].values
    r['res'] = res

    # metrics against the observed WQI (only rows with a valid observed WQI)
    valid = res[res['WQI_observed'].notna()].reset_index(drop=True)
    r['n_wqi_valid'] = len(valid)
    no_wqi = res['WQI_observed'].isna()
    if no_wqi.any():
        warnings.append((config.WARNING_NO_WQI.format(n=int(no_wqi.sum())),
                         int(no_wqi.sum()), _row_list(res['Original_row'][no_wqi])))
    if len(valid):
        met_lr = metrics.compute_metrics(valid['WQI_observed'], valid['Prediction_LR'])
        met_dt = metrics.compute_metrics(valid['WQI_observed'], valid['Prediction_DT'])
        r['metrics'] = {'lr': met_lr, 'dt': met_dt}
        # medians of the WQI axis calculated on the same rows
        r['medians'] = {'observed': float(valid['WQI_observed'].median()),
                        'lr': float(valid['Prediction_LR'].median()),
                        'dt': float(valid['Prediction_DT'].median())}
        r['error_bands'] = {
            'lr': metrics.error_band_percentages(valid['WQI_observed'], valid['Prediction_LR']),
            'dt': metrics.error_band_percentages(valid['WQI_observed'], valid['Prediction_DT']),
        }
        zeros = met_lr['zero_indices']
        if zeros:
            warnings.append((config.WARNING_WQI_ZERO.format(n=len(zeros)), len(zeros),
                             _row_list(valid['Original_row'].iloc[zeros])))
    else:
        r['medians'] = {'observed': None,
                        'lr': float(res['Prediction_LR'].median()),
                        'dt': float(res['Prediction_DT'].median())}

    # comparison between sampling sites (needs a valid observed WQI)
    if r['has_site_column'] and len(valid):
        r['sites'] = metrics.site_table(valid[config.SITE_COLUMN], valid['WQI_observed'],
                                        valid['Prediction_LR'], valid['Prediction_DT'])
        r['has_sites'] = len(r['sites']) > 0

    return r


# ---------------------------------------------------------------------------
# Excel
# ---------------------------------------------------------------------------
def _excel_value(value, sufficient=True):
    if not sufficient:
        return config.INSUFFICIENT_DATA
    if value is None:
        return config.NOT_APPLICABLE
    return float(value)


def _adjust_widths(sheet):
    for column in sheet.columns:
        longest = max((len(str(c.value)) for c in column if c.value is not None), default=8)
        sheet.column_dimensions[column[0].column_letter].width = min(max(10, longest + 2), 60)


def predictions_for_excel(res):
    """Predictions sheet with the Excel headers (only when writing)."""
    names = dict(config.EXCEL_PREDICTION_COLUMNS)
    for c in config.VARIABLE_ORDER:
        names[c] = config.USED_IN_MODEL_FORMAT.format(abbreviation=display_name(c))
    return res.rename(columns=names)


def build_excel(r):
    """Excel file "Export results (.xlsx)". Sheets in a fixed order."""
    status = config.STATUS_OK if not r['blocks'] else \
        config.STATUS_BLOCKED.format(reason=config.BLOCK_REASONS_SEPARATOR.join(r['blocks']))
    pct = 100 * r['rows_removed'] / r['rows_read'] if r['rows_read'] else 0.0
    items = config.SUMMARY_ITEMS
    summary = [
        (items['file'], r['file_name']),
        (items['generated_at'], datetime.now(timezone.utc).strftime(config.GENERATED_AT_FORMAT)),
        (items['status'], status),
        (items['rows_read'], r['rows_read']),
        (items['rows_removed'], r['rows_removed']),
        (items['pct_removed'], pct),
    ]
    if r['res'] is not None:
        summary += [
            (items['rows_predicted'], len(r['res'])),
            (items['rows_wqi_observed'], r['n_wqi_valid']),
            (items['cells_imputed'], r['cells_imputed']),
            (items['values_winsorized'], r['values_winsorized']),
        ]

    sheets = [(config.SHEET_SUMMARY, pd.DataFrame(summary, columns=config.SUMMARY_COLUMNS))]

    if r['res'] is not None:
        sheets.append((config.SHEET_PREDICTIONS, predictions_for_excel(r['res'])))

        rows = []
        for key, label, unit in config.EXCEL_METRICS_ROWS:
            if r['metrics'] is None:
                rows.append((label, config.INSUFFICIENT_DATA, config.INSUFFICIENT_DATA, unit))
            else:
                rows.append((label, _excel_value(r['metrics']['lr'][key]),
                             _excel_value(r['metrics']['dt'][key]), unit))
        for i, (_, label, _, _) in enumerate(config.ERROR_BANDS):
            unit = config.EXCEL_ERROR_BANDS_UNIT
            if r['error_bands'] is None:
                rows.append((label, config.INSUFFICIENT_DATA, config.INSUFFICIENT_DATA, unit))
            else:
                rows.append((label, r['error_bands']['lr'][i], r['error_bands']['dt'][i], unit))
        sheets.append((config.SHEET_METRICS, pd.DataFrame(rows, columns=config.EXCEL_METRICS_COLUMNS)))

        if r['has_sites']:
            rows = []
            for s in r['sites']:
                row = [s['site'], s['n']]
                for key in ('R2', 'MAE', 'MAPE', 'RMSE'):
                    for model in ('lr', 'dt'):
                        m = s[model]
                        row.append(_excel_value(m[key] if m else None, s['sufficient']))
                rows.append(row)
            sheets.append((config.SHEET_SITES, pd.DataFrame(rows, columns=config.EXCEL_SITES_COLUMNS)))

    if r['removed'] is not None:
        sheets.append((config.SHEET_REMOVED, r['removed']))
    if r['adjustments'] is not None:
        sheets.append((config.SHEET_ADJUSTMENTS, r['adjustments']))
    warnings = pd.DataFrame(r['warnings'], columns=config.EXCEL_WARNINGS_COLUMNS)
    sheets.append((config.SHEET_WARNINGS, warnings))

    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
        for sheet_name, table in sheets:
            table.to_excel(writer, sheet_name=sheet_name, index=False)
        for sheet in writer.book.worksheets:
            _adjust_widths(sheet)
            sheet.freeze_panes = 'A2'
            for cell in sheet[1]:
                cell.font = cell.font.copy(bold=True)
        if r['res'] is not None and config.DATE_COLUMN in r['res'].columns:
            sheet = writer.book[config.SHEET_PREDICTIONS]
            col = list(r['res'].columns).index(config.DATE_COLUMN) + 1
            for row in sheet.iter_rows(min_row=2, min_col=col, max_col=col):
                row[0].number_format = config.EXCEL_DATE_FORMAT
    return buffer.getvalue()


def export_file_name(name):
    base = os.path.splitext(os.path.basename(name))[0]
    base = re.sub(r'[^\w\-]+', '_', base).strip('_') or config.EXPORT_DEFAULT_NAME
    return f"{config.EXPORT_FILE_PREFIX}{base}.xlsx"


def build_template():
    """Template of the "Download template" button."""
    columns = [config.SITE_COLUMN, config.DATE_COLUMN] + \
        [display_name(c) for c in config.VARIABLE_ORDER + [config.TON_COLUMN, config.WQI_COLUMN]]
    dictionary = [(display_name(s), n, u, config.TEMPLATE_YES, '')
                  for s, n, u in config.VARIABLE_DICTIONARY]
    dictionary += list(config.TEMPLATE_OPTIONAL_COLUMNS)
    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
        pd.DataFrame(columns=columns).to_excel(writer, sheet_name=config.TEMPLATE_SHEET_DATA,
                                               index=False)
        pd.DataFrame(dictionary, columns=config.TEMPLATE_DICTIONARY_COLUMNS).to_excel(
            writer, sheet_name=config.TEMPLATE_SHEET_DICTIONARY, index=False)
        for sheet in writer.book.worksheets:
            _adjust_widths(sheet)
            for cell in sheet[1]:
                cell.font = cell.font.copy(bold=True)
    return buffer.getvalue()

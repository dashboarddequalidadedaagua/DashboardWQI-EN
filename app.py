"""
Water Quality Dashboard (WQI)
Machine Learning Approach to WQI prediction

Compares two predictive models (Linear Regression and Decision Tree) in the
prediction of the Water Quality Index (WQI) and, if the spreadsheet has an
observed WQI, measures the error of each model against it (overall and per
sampling site).

How to run (in the wqi_en folder):
    C:\\v\\Scripts\\streamlit.exe run app.py

Files expected in the same folder:
    linear_regression_model.pk, decision_tree_model.pk, scaler.pk,
    knn_imputer.pk, config.py, metrics.py, processing.py
"""

import os

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

import config
import metrics
import processing
from metrics import format_number, format_pair

st.set_page_config(page_title=config.PAGE_TITLE, layout="wide",
                   initial_sidebar_state="collapsed")

COLOR_LR = config.COLOR_LR
COLOR_DT = config.COLOR_DT


# ---------------------------------------------------------------------------
# Cache: models loaded once; processing and Excel once per file
# ---------------------------------------------------------------------------
@st.cache_resource
def load_models():
    return processing.load_models()


@st.cache_data(show_spinner=False)
def process_file(name, data):
    return processing.process(name, data, load_models())


@st.cache_data(show_spinner=False)
def results_excel(name, data):
    return processing.build_excel(process_file(name, data))


@st.cache_data(show_spinner=False)
def template_excel():
    return processing.build_template()


@st.cache_data(show_spinner=False)
def example_dataset_bytes():
    path = os.path.join(processing.FOLDER, config.EXAMPLE_DATASET_FILE)
    with open(path, 'rb') as f:
        return f.read()


# ---------------------------------------------------------------------------
# Charts
# ---------------------------------------------------------------------------
def _layout(fig, **kwargs):
    """Common layout: white background, text in the text color, light grid,
    larger titles and bars with rounded corners."""
    fig.update_layout(separators=config.PLOTLY_SEPARATORS, **kwargs)
    fig.update_layout(paper_bgcolor=config.COLOR_BACKGROUND, plot_bgcolor=config.COLOR_BACKGROUND,
                      font=dict(color=config.COLOR_TEXT))
    if fig.layout.title.text:   # without a title, the title font would show "undefined"
        fig.update_layout(title_font=dict(size=config.CHART_TITLE_SIZE,
                                          color=config.COLOR_TEXT))
    fig.update_xaxes(gridcolor=config.COLOR_GRID)
    fig.update_yaxes(gridcolor=config.COLOR_GRID)
    fig.update_traces(marker_cornerradius=config.BAR_CORNER_RADIUS, selector=dict(type='bar'))
    return fig


def show_chart(fig, key, axis=False):
    st.plotly_chart(fig, width='stretch', key=key,
                    config=config.PLOTLY_CONFIG_AXIS if axis else config.PLOTLY_CONFIG)


def _wqi_texts(values):
    """WQI values already formatted for the hover text."""
    return [format_number(v, config.DECIMALS_WQI) for v in values]


def _ideal_line(fig, lo, hi, name):
    """Dashed y = x line (Predicted vs. Observed and Scatter Plot)."""
    fig.add_scatter(x=[lo, hi], y=[lo, hi], mode='lines', name=name,
                    line=dict(color=config.COLOR_IDEAL_LINE, dash='dash'),
                    customdata=_wqi_texts([lo, hi]), hovertemplate=config.HOVER_IDEAL_LINE)


def monitoring_chart(dates, y, color, name, y_axis_title):
    """Water quality monitoring chart of one sampling site:
    mean line = mean WQI of the plotted points, lower and upper thresholds
    fixed (config), X on the samples with WQI up to the lower threshold (poor
    or very poor) and diamond on the samples with WQI above the upper
    threshold (excellent). Returns (fig, count_low, count_high, total), with
    total = number of points drawn."""
    y = pd.Series(y, dtype=float).reset_index(drop=True)
    dates = pd.Series(dates).reset_index(drop=True)
    hover_data = np.column_stack([dates.dt.strftime(config.DATE_FORMAT_HOVER), _wqi_texts(y),
                                  [metrics.wqi_category(v) for v in y]])
    mean = y.mean()
    lower, upper = config.MONITORING_LOWER_THRESHOLD, config.MONITORING_UPPER_THRESHOLD

    fig = go.Figure()
    fig.add_scatter(x=dates, y=y, mode='markers', name=name, marker=dict(color=color, size=5),
                    cliponaxis=False, customdata=hover_data, hovertemplate=config.HOVER_MONITORING)
    font = dict(color=config.COLOR_TEXT)
    fig.add_hline(y=mean, line_dash='dash', line_color=config.COLOR_MEAN_LINE,
                  annotation_text=config.CHART_MEAN.format(v=format_number(mean, config.DECIMALS_WQI)),
                  annotation_position='top left', annotation_font=font,
                  annotation_bgcolor=config.COLOR_BACKGROUND)
    fig.add_hline(y=upper, line_dash='dot', line_color=config.COLOR_MONITORING_THRESHOLDS,
                  annotation_text=config.CHART_UPPER_THRESHOLD.format(v=upper),
                  annotation_position='bottom right', annotation_font=font,
                  annotation_bgcolor=config.COLOR_BACKGROUND)
    fig.add_hline(y=lower, line_dash='dot', line_color=config.COLOR_MONITORING_THRESHOLDS,
                  annotation_text=config.CHART_LOWER_THRESHOLD.format(v=lower),
                  annotation_position='bottom right', annotation_font=font,
                  annotation_bgcolor=config.COLOR_BACKGROUND)
    low, high = metrics.classify_monitoring(y)
    if low.any():
        fig.add_scatter(x=dates[low], y=y[low], mode='markers', name=config.CHART_WQI_POOR,
                        marker=dict(color=config.COLOR_POOR_MARKER, size=11, symbol='x'),
                        cliponaxis=False, customdata=hover_data[low],
                        hovertemplate=config.HOVER_MONITORING)
    if high.any():
        fig.add_scatter(x=dates[high], y=y[high], mode='markers', name=config.CHART_WQI_EXCELLENT,
                        marker=dict(color=config.COLOR_EXCELLENT_MARKER, size=10, symbol='diamond'),
                        cliponaxis=False, customdata=hover_data[high],
                        hovertemplate=config.HOVER_MONITORING)

    # Y axis from 0 to 100, extended if a value is outside this range
    margin = config.MONITORING_AXIS_MARGIN
    lo = config.WQI_MIN if y.min() >= config.WQI_MIN else np.floor(y.min()) - margin
    hi = config.WQI_MAX if y.max() <= config.WQI_MAX else np.ceil(y.max()) + margin
    fig.update_yaxes(range=[lo, hi])
    fig.update_xaxes(tickformat=config.DATE_FORMAT_AXIS, hoverformat=config.DATE_FORMAT_HOVER)
    _layout(fig, title=config.CHART_MONITORING_TITLE.format(name=name),
            xaxis_title=config.CHART_AXIS_DATE, yaxis_title=y_axis_title,
            legend=dict(orientation='h', y=1.12))
    return fig, int(low.sum()), int(high.sum()), len(y)


def scatter_chart(res):
    """LR vs. DT scatter plot with the identity line."""
    lo = min(res['Prediction_LR'].min(), res['Prediction_DT'].min())
    hi = max(res['Prediction_LR'].max(), res['Prediction_DT'].max())
    fig = go.Figure()
    fig.add_scatter(x=res['Prediction_LR'], y=res['Prediction_DT'],
                    mode='markers', name=config.CHART_SAMPLES,
                    marker=dict(color=config.COLOR_SCATTER, opacity=0.6),
                    customdata=np.column_stack([_wqi_texts(res['Prediction_LR']),
                                                _wqi_texts(res['Prediction_DT'])]),
                    hovertemplate=config.HOVER_SCATTER)
    _ideal_line(fig, lo, hi, config.CHART_AGREEMENT_LINE)
    return _layout(fig, title=config.CHART_SCATTER_TITLE,
                   xaxis_title=config.CHART_AXIS_PREDICTED_LR,
                   yaxis_title=config.CHART_AXIS_PREDICTED_DT,
                   legend=dict(orientation='h', y=1.12))


def _label_side(x):
    """+1 (label to the right of the line) or -1 (to the left, close to 100)."""
    return -1 if x > config.WQI_MAX - config.AXIS_LABEL_MARGIN else 1


def wqi_axis_chart(medians):
    """WQI axis from 0 to 100 with the official categories (proportional
    widths), the numbers of the boundaries and one vertical line per series
    (median), each one in its third of the height: Observed at the top, LR in
    the middle, DT at the bottom."""
    fig = go.Figure()
    font = dict(color=config.COLOR_AXIS_TEXT)

    for name, lo, hi, color, _ in config.WQI_CATEGORIES:
        fig.add_shape(type='rect', x0=lo, x1=hi, y0=0, y1=1, fillcolor=color,
                      line=dict(color=config.COLOR_BACKGROUND, width=2), layer='below')
        # category name right below the rectangle: the 3 lines are inside it
        fig.add_annotation(x=(lo + hi) / 2, y=-0.04, yanchor='top',
                           text=config.CATEGORY_LABEL_FORMAT.format(name=name),
                           showarrow=False, font=dict(size=14, **font))
    numbers = [(config.WQI_MIN, 'left'), (config.WQI_MAX, 'right')]
    numbers += [(b, 'center') for b in config.WQI_BOUNDARIES]
    for x, anchor in numbers:
        fig.add_annotation(x=x, y=1.12, text=str(x), showarrow=False,
                           xanchor=anchor, font=dict(size=12, **font))

    height = 1 / 3
    for key, label, third, _ in config.AXIS_LINES:
        x = medians[key]
        if x is None:
            continue
        y0, y1 = third * height, (third + 1) * height
        fig.add_shape(type='line', x0=x, x1=x, y0=y0 + 0.03, y1=y1 - 0.03,
                      line=dict(color=config.COLOR_AXIS_SERIES[key], width=3))
        side = _label_side(x)
        fig.add_annotation(x=x, y=(y0 + y1) / 2, text=label, showarrow=False,
                           xanchor='left' if side > 0 else 'right', xshift=5 * side,
                           font=dict(size=12, color=config.COLOR_TEXT))

    fig.update_xaxes(range=[config.WQI_MIN - 1, config.WQI_MAX + 1], visible=False, fixedrange=True)
    fig.update_yaxes(range=config.WQI_AXIS_RANGE_Y, visible=False, fixedrange=True)
    return _layout(fig, height=config.WQI_AXIS_HEIGHT, margin=dict(l=10, r=10, t=10, b=10),
                   showlegend=False, dragmode=False)


def predicted_observed_chart(valid, column, color, title):
    """Predicted vs. Observed of one model, with the ideal line y = x and the
    category boundaries."""
    y_observed = valid['WQI_observed']
    y_predicted = valid[column]
    minimum = min(y_observed.min(), y_predicted.min())
    maximum = max(y_observed.max(), y_predicted.max())
    lo = config.WQI_MIN if minimum >= config.WQI_MIN else np.floor(minimum) - 2
    hi = config.WQI_MAX if maximum <= config.WQI_MAX else np.ceil(maximum) + 2

    fig = go.Figure()
    for b in config.WQI_BOUNDARIES:
        line = dict(color=config.COLOR_CATEGORY_BOUNDARY, width=1)
        fig.add_shape(type='line', x0=b, x1=b, y0=lo, y1=hi, line=line, layer='below')
        fig.add_shape(type='line', x0=lo, x1=hi, y0=b, y1=b, line=line, layer='below')
    fig.add_scatter(x=y_observed, y=y_predicted, mode='markers', name=config.CHART_SAMPLES,
                    marker=dict(color=color, opacity=config.PREDICTED_OBSERVED_OPACITY),
                    customdata=np.column_stack([_wqi_texts(y_observed), _wqi_texts(y_predicted)]),
                    hovertemplate=config.HOVER_PREDICTED_OBSERVED)
    _ideal_line(fig, lo, hi, config.IDEAL_LINE_LEGEND)
    fig.update_xaxes(range=[lo, hi], title=config.PREDICTED_OBSERVED_X_AXIS)
    fig.update_yaxes(range=[lo, hi], title=config.PREDICTED_OBSERVED_Y_AXIS)
    return _layout(fig, title=title, height=480, legend=dict(orientation='h', y=1.1))


def error_bands_chart(bands):
    """% of the samples of each model in each absolute error band (grouped bars)."""
    labels = [b[0] for b in config.ERROR_BANDS]
    fig = go.Figure()
    for key, color, name in (('lr', COLOR_LR, config.NAME_LR), ('dt', COLOR_DT, config.NAME_DT)):
        texts = [format_number(v, config.DECIMALS_PCT, config.PCT_SUFFIX) for v in bands[key]]
        fig.add_bar(x=labels, y=bands[key], name=name, marker_color=color,
                    text=texts, textposition='outside', textangle=0, cliponaxis=False,
                    textfont=dict(color=config.COLOR_TEXT),
                    customdata=[[name, lab, t] for lab, t in zip(labels, texts)],
                    hovertemplate=config.HOVER_ERROR_BANDS)
    maximum = max(bands['lr'] + bands['dt'])
    fig.update_yaxes(range=[0, maximum * config.ERROR_BANDS_AXIS_HEADROOM],
                     ticksuffix=config.PCT_SUFFIX)
    return _layout(fig, barmode='group', xaxis_title=config.CHART_ERROR_BANDS_X_AXIS,
                   yaxis_title=config.CHART_ERROR_BANDS_Y_AXIS,
                   legend=dict(orientation='h', y=1.1))


# ---------------------------------------------------------------------------
# Screen blocks
# ---------------------------------------------------------------------------
def intro_text():
    st.subheader(config.INTRO_TITLE, anchor=False)
    st.markdown(config.INTRO_PARAGRAPH)
    st.markdown(config.INTRO_LINE)
    st.markdown(f"**{config.INTRO_SUBTITLE}**")
    st.markdown("\n".join(f"- {item}" for item in config.INTRO_ITEMS))


def template_button(key):
    st.download_button(config.BUTTON_DOWNLOAD_TEMPLATE, template_excel(),
                       file_name=config.TEMPLATE_FILE_NAME,
                       mime=config.MIME_XLSX, key=key, on_click='ignore')


def export_button(name, data, key):
    st.download_button(config.BUTTON_EXPORT, results_excel(name, data),
                       file_name=processing.export_file_name(name),
                       mime=config.MIME_XLSX, key=key, on_click='ignore')


def use_example_dataset():
    st.session_state['source'] = 'example'
    # new key in the file uploader: the upload field becomes empty again
    st.session_state['n_uploader'] = st.session_state.get('n_uploader', 0) + 1


def site_selector(sites, key):
    """Sampling Site selector. The key carries the number of the dataset: when
    the dataset changes, the selector goes back to the first site of the list."""
    return st.selectbox(config.SITE_SELECTOR_LABEL, sites, index=0,
                        key=f"{key}_{st.session_state.get('n_dataset', 0)}")


def wqi_axis_with_legend(medians):
    show_chart(wqi_axis_chart(medians), key='chart_wqi_axis', axis=True)
    lines = [config.COLOR_SQUARE_FORMAT.format(
                 color=config.COLOR_AXIS_SERIES[key],
                 text=legend.format(v=format_number(medians[key], config.DECIMALS_WQI)))
             for key, _, _, legend in config.AXIS_LINES if medians[key] is not None]
    st.markdown("  \n".join(lines))
    note = config.AXIS_NOTE_MEDIAN
    if medians['observed'] is not None:
        note += " " + config.AXIS_NOTE_ERROR
    st.caption(note)


def monitoring_data(r, column):
    """Rows that go into the monitoring charts (valid date, site and value)
    or None if the spreadsheet has no Sampling Site and Date."""
    if not (r['has_date'] and r['has_site_column']):
        return None
    res = r['res']
    ok = res[config.DATE_COLUMN].notna() & res[config.SITE_COLUMN].notna() & res[column].notna()
    return res[ok]


def monitoring_summary(template, count, total, **threshold):
    """One summary line below the monitoring chart:
    percentage, count and total of samples ('1 of 1 sample')."""
    pct = 100 * count / total if total else None
    word = config.WORD_SAMPLE_SINGULAR if total == 1 else config.WORD_SAMPLE_PLURAL
    return template.format(pct=format_number(pct, config.DECIMALS_PCT, config.PCT_SUFFIX),
                           count=count, total=total, word=word, **threshold)


def monitoring_for_one_site(data, column, color, name, y_axis_title, key):
    """Selector + monitoring chart + summary of one sampling site."""
    sites = metrics.sort_sites(data[config.SITE_COLUMN])
    chosen = site_selector(sites, key=f"sel_{key}")
    sel = data[data[config.SITE_COLUMN] == chosen]
    fig, count_low, count_high, total = monitoring_chart(sel[config.DATE_COLUMN], sel[column],
                                                         color, name, y_axis_title)
    show_chart(fig, key=f"chart_{key}")
    st.markdown(monitoring_summary(config.MONITORING_LOW_FORMAT, count_low, total,
                                   lower=config.MONITORING_LOWER_THRESHOLD))
    st.markdown(monitoring_summary(config.MONITORING_HIGH_FORMAT, count_high, total,
                                   upper=config.MONITORING_UPPER_THRESHOLD))


def observed_monitoring_section(r):
    st.subheader(config.SECTION_MONITORING_OBSERVED, anchor=False)
    st.markdown(config.MONITORING_OBSERVED_TEXT)
    data = monitoring_data(r, 'WQI_observed')
    if data is None or data.empty:
        st.info(config.INFO_MONITORING_MISSING_COLUMNS)
        return
    monitoring_for_one_site(data, 'WQI_observed', config.COLOR_TEXT, config.CHART_OBSERVED_NAME,
                            config.CHART_AXIS_WQI_OBSERVED, key='monitoring_observed')


def predicted_monitoring_section(r):
    st.subheader(config.SECTION_MONITORING_PREDICTED, anchor=False)
    st.markdown(config.MONITORING_PREDICTED_TEXT)
    data = monitoring_data(r, 'Prediction_LR')
    if data is None or data.empty:
        st.info(config.INFO_MONITORING_MISSING_COLUMNS)
        return
    col1, col2 = st.columns(2)
    with col1:
        monitoring_for_one_site(data, 'Prediction_LR', COLOR_LR, config.NAME_LR,
                                config.CHART_AXIS_WQI_PREDICTED, key='monitoring_lr')
    with col2:
        monitoring_for_one_site(data, 'Prediction_DT', COLOR_DT, config.NAME_DT,
                                config.CHART_AXIS_WQI_PREDICTED, key='monitoring_dt')


def overview_subtab(r, name, data):
    with st.container(border=True):
        st.markdown(config.ABBREVIATIONS_LEGEND, text_alignment='center')
    wqi_axis_with_legend(r['medians'])

    if r['metrics'] is not None:
        met_lr, met_dt = r['metrics']['lr'], r['metrics']['dt']
        columns = st.columns(len(config.METRIC_CARDS))
        for col, card in zip(columns, config.METRIC_CARDS):
            key, title, text, badges, suffix, decimals, direction = card
            highlight = metrics.better_model(met_lr[key], met_dt[key], decimals, direction)
            with col:
                with st.container(border=True, height='stretch'):
                    st.markdown(f"**{title}**")
                    st.markdown(format_pair(met_lr[key], met_dt[key], decimals, suffix, highlight))
                    st.caption(text)
                    with st.container(horizontal=True, gap='small'):
                        for badge in badges:
                            st.badge(badge, color='gray')

        valid = r['res'][r['res']['WQI_observed'].notna()]
        g1, g2 = st.columns(2)
        with g1:
            show_chart(predicted_observed_chart(valid, 'Prediction_LR', COLOR_LR,
                                                config.TITLE_PREDICTED_OBSERVED_LR),
                       key='chart_po_lr')
        with g2:
            show_chart(predicted_observed_chart(valid, 'Prediction_DT', COLOR_DT,
                                                config.TITLE_PREDICTED_OBSERVED_DT),
                       key='chart_po_dt')

        st.subheader(config.ERROR_BANDS_TITLE, anchor=False)
        st.markdown(config.ERROR_BANDS_TEXT)
        show_chart(error_bands_chart(r['error_bands']), key='chart_error_bands')

        observed_monitoring_section(r)

    export_button(name, data, key='export_overview')


def predictions_subtab(r, name, data):
    st.subheader(config.SECTION_SCATTER, anchor=False)
    st.markdown(config.SCATTER_TEXT)
    show_chart(scatter_chart(r['res']), key='chart_scatter')

    predicted_monitoring_section(r)

    export_button(name, data, key='export_predictions')


def site_table_for_screen(sites):
    rows = []
    for s in sites:
        if not s['sufficient']:
            cells = [config.INSUFFICIENT_DATA] * 4
        else:
            cells = [
                format_pair(s['lr']['R2'], s['dt']['R2'], config.DECIMALS_R2),
                format_pair(s['lr']['MAE'], s['dt']['MAE'], config.DECIMALS_WQI),
                format_pair(s['lr']['MAPE'], s['dt']['MAPE'], config.DECIMALS_MAPE,
                            suffix=config.PCT_SUFFIX),
                format_pair(s['lr']['RMSE'], s['dt']['RMSE'], config.DECIMALS_WQI),
            ]
        rows.append([s['site'], s['n']] + cells)
    return pd.DataFrame(rows, columns=config.SITES_TABLE_COLUMNS)


def show_site_table(table):
    """Sampling site table with the MAE column highlighted (cell background
    and bold header)."""
    highlight = config.SITES_HIGHLIGHT_COLUMN
    column = list(table.columns).index(highlight)
    style = (table.style
             .set_properties(subset=[highlight], **{'background-color': config.COLOR_TABLE_HIGHLIGHT})
             .set_table_styles([{'selector': f'th.col_heading.col{column}',
                                 'props': [('font-weight', 'bold'),
                                           ('background-color', config.COLOR_TABLE_HIGHLIGHT)]}]))
    st.table(style, hide_index=True)


def sites_subtab(r, name, data):
    st.info(config.SITES_NOTE)
    table = site_table_for_screen(r['sites'])
    chosen = site_selector(list(table[config.SITES_TABLE_COLUMNS[0]]), key='sel_site_table')
    show_site_table(table[table[config.SITES_TABLE_COLUMNS[0]] == chosen])
    show_site_table(table)
    export_button(name, data, key='export_sites')


def about_tab():
    st.subheader(config.ABOUT_VARIABLES_TITLE, anchor=False)
    st.dataframe(pd.DataFrame(config.ABOUT_VARIABLES, columns=config.ABOUT_VARIABLES_COLUMNS),
                 hide_index=True)

    st.subheader(config.ABOUT_MODEL_DETAILS_TITLE, anchor=False)
    lr, dt, _, imputer = load_models()
    details = processing.model_details(lr, dt, imputer)
    st.markdown("\n".join(f"- {line.format(**details)}" for line in config.ABOUT_MODEL_DETAILS))

    st.subheader(config.ABOUT_CATEGORIES_TITLE, anchor=False)
    categories = [(name, wqi_range) for name, _, _, _, wqi_range in config.WQI_CATEGORIES]
    st.dataframe(pd.DataFrame(categories, columns=config.ABOUT_CATEGORIES_COLUMNS), hide_index=True)
    st.caption(config.WQI_CATEGORIES_SOURCE)


def analysis_tab():
    top = st.container()

    with st.container(horizontal=True, gap='small'):
        template_button(key='template_top')
        st.button(config.BUTTON_EXAMPLE_DATASET, on_click=use_example_dataset, key='example_button')

    if 'n_uploader' not in st.session_state:
        st.session_state['n_uploader'] = 0
    uploaded = st.file_uploader(config.UPLOAD_LABEL, type=config.ACCEPTED_FORMATS,
                                key=f"file_{st.session_state['n_uploader']}")

    # which dataset to show: a newly uploaded file replaces everything
    # (including the example dataset); the example button is valid until the
    # next upload
    if uploaded is not None and uploaded.file_id != st.session_state.get('upload_id'):
        st.session_state['upload_id'] = uploaded.file_id
        st.session_state['source'] = 'upload'
    if uploaded is None and st.session_state.get('source') == 'upload':
        st.session_state['source'] = None
    if uploaded is None:
        st.session_state['upload_id'] = None

    source = st.session_state.get('source')
    if source == 'upload':
        name, data = uploaded.name, uploaded.getvalue()
        dataset_id = uploaded.file_id
    elif source == 'example':
        name, data = config.EXAMPLE_DATASET_FILE, example_dataset_bytes()
        dataset_id = 'example'
    else:
        with top:
            intro_text()
        return

    # new dataset (new upload or example dataset): the sampling site
    # selectors go back to the preselected site
    if st.session_state.get('dataset_id') != dataset_id:
        st.session_state['dataset_id'] = dataset_id
        st.session_state['n_dataset'] = st.session_state.get('n_dataset', 0) + 1

    try:
        r = process_file(name, data)
    except Exception as e:
        with top:
            intro_text()
        st.error(config.BLOCK_UNEXPECTED_ERROR.format(error=e))
        template_button(key='template_block')
        return

    if r['blocks']:
        with top:
            intro_text()
        for message in r['blocks']:
            st.error(message)
        template_button(key='template_block')
        if r['read']:
            export_button(name, data, key='export_block')
        return

    with top:
        with st.expander(config.EXPANDER_PREPARE):
            intro_text()

    if source == 'example':
        st.info(config.EXAMPLE_DATASET_BANNER)

    names = [config.SUBTAB_OVERVIEW, config.SUBTAB_PREDICTIONS]
    if r['has_sites']:
        names.append(config.SUBTAB_SITES)
    subtabs = st.tabs(names)
    with subtabs[0]:
        overview_subtab(r, name, data)
    with subtabs[1]:
        predictions_subtab(r, name, data)
    if r['has_sites']:
        with subtabs[2]:
            sites_subtab(r, name, data)


# ---------------------------------------------------------------------------
# Interface
# ---------------------------------------------------------------------------
st.title(config.TITLE, anchor=False)

analysis_tab_container, about_tab_container = st.tabs([config.TAB_ANALYSIS, config.TAB_ABOUT])
with about_tab_container:
    about_tab()
with analysis_tab_container:
    analysis_tab()

"""
Fixed configuration of the WQI Dashboard.

Every text shown to the user, every fixed number (limits, bands, colors)
and every label comes from this file. app.py, processing.py and metrics.py
do not write texts or magic numbers on their own.
"""

# ---------------------------------------------------------------------------
# Original training pipeline (DO NOT CHANGE)
# scaler.pk and knn_imputer.pk store feature_names_in_ with these
# abbreviations, in this order. The same abbreviations are used everywhere:
# inside the pipeline, in the accepted spreadsheet headers and in the output
# (screen, Excel, template, warnings). There is no translation layer; the
# only display difference is PH, shown as pH (DISPLAY_NAMES).
# ---------------------------------------------------------------------------
VARIABLE_ORDER = ['BOD', 'THC', 'TOP', 'DOS', 'PH', 'TOS', 'TUR']
WINSORIZE_COLUMNS = ['BOD', 'THC', 'TOP', 'DOS', 'PH', 'TOS', 'TUR']
WINSORIZE_LIMITS = [0.1, 0.1]
COLUMNS_DROPPED_BEFORE_MODEL = ['TON', 'WQI']
JUNK_INDEX_COLUMNS = ['Unnamed: 0', 'index']

# filter of values outside the range used to train the models (same as in
# training): (minimum, maximum).
# None = no limit on that side. A row fails if value < minimum or > maximum.
FILTER_LIMITS = {
    'PH': (2, 12),
    'BOD': (None, 30),
    'DOS': (None, 140),
    'TOS': (None, 500),
    'TUR': (None, 100),
    'TON': (None, 100),
    'TOP': (None, 10),
}

MODEL_FILES = {
    'lr': 'linear_regression_model.pk',
    'dt': 'decision_tree_model.pk',
    'scaler': 'scaler.pk',
    'imputer': 'knn_imputer.pk',
}

# ---------------------------------------------------------------------------
# Spreadsheet columns
# ---------------------------------------------------------------------------
WQI_COLUMN = 'WQI'
TON_COLUMN = 'TON'
SITE_COLUMN = 'Sampling Site'
DATE_COLUMN = 'Date'
# accepted names for the date column (case-insensitive); the first matching
# column of the spreadsheet is used
ACCEPTED_DATE_NAMES = ['date', 'sampling date', 'sampling_date', 'collection date',
                       'collection_date', 'sample date', 'sample_date']
# accepted names for the Sampling Site column (case-insensitive), in order of
# priority: if there is more than one, the first one of this list is used
ACCEPTED_SITE_NAMES = ['sampling site', 'sampling_site', 'site', 'sampling point',
                       'sampling_point', 'station', 'ugrhi']
ACCEPTED_FORMATS = ['xlsx', 'xls', 'csv']

# Dates written as text are read one by one, trying these formats in order:
# first yyyy-mm-dd (also with a time after the date, e.g. "2023-02-13
# 00:00:00"), then dd/mm/yyyy. No dayfirst and no automatic format inference.
DATE_TEXT_FORMATS = ['%Y-%m-%d', '%Y-%m-%d %H:%M:%S', '%Y-%m-%d %H:%M',
                     '%Y-%m-%d %H:%M:%S.%f', '%Y-%m-%dT%H:%M:%S', '%Y-%m-%dT%H:%M',
                     '%Y-%m-%dT%H:%M:%S.%f', '%d/%m/%Y']

# Abbreviation shown on screen, Excel, template and warnings when it is not
# the internal abbreviation itself (all others are shown as they are).
DISPLAY_NAMES = {
    'PH': 'pH',
}

# Required variables (the 7 of the model): internal abbreviation, name,
# unit. Generates the required rows of the template.
VARIABLE_DICTIONARY = [
    ('BOD', 'Biochemical oxygen demand', 'mg/L'),
    ('THC', 'Thermotolerant coliforms (E. coli)', 'CFU/100 mL'),
    ('TOP', 'Total phosphorus', 'mg/L'),
    ('DOS', 'Dissolved oxygen saturation', '% saturation'),
    ('PH', 'pH', 'unitless'),
    ('TOS', 'Total solids', 'mg/L'),
    ('TUR', 'Turbidity', 'NTU'),
]
TEMPLATE_YES = 'Yes'
TEMPLATE_NO = 'No'
# Optional columns of the template: column, name, unit, required,
# also accepted as
TEMPLATE_OPTIONAL_COLUMNS = [
    (SITE_COLUMN, 'Sampling site (code or name of the station or basin)', 'unitless',
     TEMPLATE_NO, 'Site, Sampling Point, Station, UGRHI'),
    (DATE_COLUMN, 'Sampling date', 'dd/mm/yyyy or yyyy-mm-dd', TEMPLATE_NO,
     'Sampling Date, Collection Date, Sample Date'),
    ('TON', 'Total nitrogen (used only in the data quality filter)', 'mg/L', TEMPLATE_NO, ''),
    ('WQI', 'Observed WQI (to compare with the predictions)', 'unitless', TEMPLATE_NO, ''),
]

# Unit check in the header (e.g. "BOD (mg/L)").
# Accepted forms, compared without spaces and case-insensitive.
ACCEPTED_UNITS = {
    'BOD': ['mg/l', 'mgl'],
    'THC': ['cfu/100ml', 'mpn/100ml', 'cfu/100', 'mpn/100'],
    'TOP': ['mg/l', 'mgl'],
    'DOS': ['%', '%sat', '%saturation'],
    'PH': ['', 'unitless', '-'],
    'TOS': ['mg/l', 'mgl'],
    'TUR': ['ntu'],
    'TON': ['mg/l', 'mgl'],
    'WQI': ['', 'unitless', '-'],
}

# ---------------------------------------------------------------------------
# WQI categories (CETESB 2023 report on inland water quality in the State of
# Sao Paulo)
# (name, exclusive lower limit, inclusive upper limit, color, range)
# ---------------------------------------------------------------------------
WQI_CATEGORIES = [
    ('Very poor', 0, 19, '#f28b82', 'up to 19'),
    ('Poor', 19, 36, '#f9b16e', 'above 19 up to 36'),
    ('Fair', 36, 51, '#f6dc5c', 'above 36 up to 51'),
    ('Good', 51, 79, '#8fd18a', 'above 51 up to 79'),
    ('Excellent', 79, 100, '#6cc4c0', 'above 79 up to 100'),
]
WQI_BOUNDARIES = [19, 36, 51, 79]
WQI_MIN = 0
WQI_MAX = 100
WQI_CATEGORIES_SOURCE = "Source: CETESB, 2023. WQI as defined by CETESB."

# ---------------------------------------------------------------------------
# Absolute error bands |observed WQI - prediction|. The upper limit belongs
# to the band (same rule as the CETESB categories).
# (chart label, Excel label, exclusive lower limit, inclusive upper limit).
# None = no limit on that side (the first band starts at 0, inclusive).
# ---------------------------------------------------------------------------
ERROR_BANDS = [
    ("up to 5", "% of samples with error up to 5", None, 5),
    ("above 5 up to 10", "% of samples with error above 5 up to 10", 5, 10),
    ("above 10 up to 15", "% of samples with error above 10 up to 15", 10, 15),
    ("above 15", "% of samples with error above 15", 15, None),
]

# ---------------------------------------------------------------------------
# Sampling Sites
# ---------------------------------------------------------------------------
MIN_ROWS_PER_SITE = 2

# ---------------------------------------------------------------------------
# Water quality monitoring charts: fixed and arbitrary thresholds (lower
# threshold and upper threshold), based on the CETESB categories. The mean
# line is the mean WQI of the plotted points of the selected sampling site.
# Same rule as the categories: the upper limit belongs to the category (poor
# or very poor = WQI up to the lower threshold; excellent = WQI above the
# upper threshold).
# ---------------------------------------------------------------------------
MONITORING_LOWER_THRESHOLD = 36
MONITORING_UPPER_THRESHOLD = 79

# ---------------------------------------------------------------------------
# Colors and formats
# ---------------------------------------------------------------------------
# model colors validated for color blindness and contrast
COLOR_LR = '#0057e7'                    # blue
COLOR_DT = '#c84a00'                    # dark orange
COLOR_TEXT = '#0f172a'
COLOR_TEXT_SECONDARY = '#475569'
COLOR_AXIS_TEXT = COLOR_TEXT_SECONDARY
COLOR_BACKGROUND = '#ffffff'
COLOR_BACKGROUND_SECONDARY = '#eef2f8'
COLOR_BORDER = '#d6deea'
COLOR_GRID = '#e5e9f0'
COLOR_CATEGORY_BOUNDARY = '#d1d5db'
COLOR_MEAN_LINE = '#334155'             # mean line of the monitoring charts
COLOR_MONITORING_THRESHOLDS = '#94a3b8'  # upper and lower thresholds
COLOR_POOR_MARKER = '#9d174d'           # X marker "Poor or very poor WQI"
COLOR_EXCELLENT_MARKER = '#15803d'      # diamond marker "Excellent WQI"
# color of each series on the WQI axis (lines and legend squares)
COLOR_AXIS_SERIES = {'observed': COLOR_TEXT, 'lr': COLOR_LR, 'dt': COLOR_DT}
COLOR_SCATTER = '#475569'               # points of the LR vs. DT scatter plot
COLOR_IDEAL_LINE = '#0f172a'            # dashed y = x lines
COLOR_TABLE_HIGHLIGHT = '#e3ecfd'       # MAE column in the sampling site tables
CHART_TITLE_SIZE = 17
BAR_CORNER_RADIUS = 4
ERROR_BANDS_AXIS_HEADROOM = 1.15        # space above the tallest bar for the label

# decimal places on screen (rounding like Excel's ROUND: ties go away from
# zero). Internal calculations and the Excel file use the full value.
DECIMALS_WQI = 1    # WQI, MAE, RMSE, medians, means, mean line of the monitoring charts
DECIMALS_PCT = 1    # percentages in general (including the error band labels)
DECIMALS_R2 = 2
DECIMALS_MAPE = 2
DATE_FORMAT_AXIS = '%b %Y'
DATE_FORMAT_HOVER = '%Y-%m-%d'
PLOTLY_SEPARATORS = '.,'
# locale 'en': month names on the date axes are always in English, whatever
# the language of the computer
PLOTLY_CONFIG = {
    'toImageButtonOptions': {'format': 'png', 'scale': 3},
    'displaylogo': False,
    'locale': 'en',
}
PLOTLY_CONFIG_AXIS = {
    'toImageButtonOptions': {'format': 'png', 'scale': 3},
    'displaylogo': False,
    'locale': 'en',
    'modeBarButtonsToRemove': ['zoom2d', 'pan2d', 'select2d', 'lasso2d',
                               'zoomIn2d', 'zoomOut2d', 'autoScale2d',
                               'resetScale2d'],
}
PREDICTED_OBSERVED_OPACITY = 0.5
HIGH_REMOVAL_ALERT_PCT = 80

# separators and small formats of visible texts
LIST_SEPARATOR = ', '                   # missing columns, lists of original rows
ROW_LIST_TRUNCATION = ' ...'            # end of a list of rows that is too long
REASON_SEPARATOR = '; '                 # several reasons for the same removed row
BLOCK_REASONS_SEPARATOR = ' '           # several blocks in the Status of the Summary
CATEGORY_LABEL_FORMAT = "<b>{name}</b>"  # WQI category names below the WQI axis

# ---------------------------------------------------------------------------
# Texts: top and tabs
# ---------------------------------------------------------------------------
PAGE_TITLE = "Water Quality Dashboard (WQI)"
TITLE = "Water Quality Dashboard (WQI)"

TAB_ANALYSIS = "Analyze Your Data"
TAB_ABOUT = "About the Dashboard"
SUBTAB_OVERVIEW = "Overview"
SUBTAB_PREDICTIONS = "Model Predictions"
SUBTAB_SITES = "Sampling Site Comparison"

# ---------------------------------------------------------------------------
# Texts: introduction
# ---------------------------------------------------------------------------
INTRO_TITLE = "Compare the models' predictions with the observed WQI in your data"
INTRO_PARAGRAPH = (
    "This dashboard uses two machine learning models, Linear Regression and Decision "
    "Tree, to predict the WQI (Water Quality Index) from 7 variables measured in the "
    "water. Upload your spreadsheet and the dashboard shows how large each model's "
    "errors are, how the two models compare with each other and, if the spreadsheet "
    "has a Sampling Site column, how the results vary across sampling sites."
)
INTRO_LINE = ("Download the template to see the expected format and use exactly the "
              "same column names.")
INTRO_SUBTITLE = "Before uploading, check:"
INTRO_ITEMS = [
    "Formats: .xlsx, .xls or .csv",
    "Empty cells in the variables: allowed, and filled using the models' method.",
    "Extreme values: adjusted using the models' method.",
]
EXPANDER_PREPARE = "How to prepare your spreadsheet"

BUTTON_DOWNLOAD_TEMPLATE = "Download template"
BUTTON_EXAMPLE_DATASET = "Use example dataset"
BUTTON_EXPORT = "Export results (.xlsx)"
UPLOAD_LABEL = "Upload your spreadsheet"
EXAMPLE_DATASET_BANNER = "You are viewing the example dataset (CETESB, 2023)"

EXAMPLE_DATASET_FILE = 'UGRHI23_example.xlsx'
TEMPLATE_FILE_NAME = 'wqi_template.xlsx'
EXPORT_FILE_PREFIX = 'wqi_results_'
EXPORT_DEFAULT_NAME = 'data'            # used when the uploaded file name has no usable characters
MIME_XLSX = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"

# ---------------------------------------------------------------------------
# Texts: blocks
# ---------------------------------------------------------------------------
BLOCK_READ = ("The file could not be read. Upload a .xlsx, .xls or .csv spreadsheet in "
              "the template format.")
BLOCK_EMPTY = "The file has no data rows."
BLOCK_COLUMNS = ("Required columns are missing: {columns}. Use exactly the column names "
                 "in the template.")
BLOCK_UNIT = ("Column {column} has the unit \"{unit}\", but the model expects {expected}. "
              "Convert the values or use the template.")
BLOCK_ALL_REMOVED = ("All rows were removed by the data quality filter because they have "
                     "values outside the range used to train the models. There is nothing "
                     "to predict. The reason for each row is in the Excel file from the "
                     "Export results button.")
BLOCK_UNEXPECTED_ERROR = "Error while processing the data: {error}"

# ---------------------------------------------------------------------------
# Texts: Overview
# ---------------------------------------------------------------------------
ABBREVIATIONS_LEGEND = "LR = Linear Regression model | DT = Decision Tree model"
NOT_APPLICABLE = "N/A"
INSUFFICIENT_DATA = "insufficient data"
PAIR_FORMAT = "LR = {lr} | DT = {dt}"
PAIR_SEPARATOR = " | "     # separates the LR part and the DT part inside PAIR_FORMAT
HIGHLIGHT_FORMAT = ":green-background[{text}]"     # highlight of the better model in the cards

# WQI axis: one vertical line per series (median), each one in its third of
# the height of the categories rectangle: (key, short label, third, legend)
# third 2 = top, 1 = middle, 0 = bottom
AXIS_LINES = [
    ('observed', "Observed", 2, "Observed = observed WQI (median) in your data: {v}"),
    ('lr', "LR", 1, "LR = WQI predicted by Linear Regression (median): {v}"),
    ('dt', "DT", 0, "DT = WQI predicted by Decision Tree (median): {v}"),
]
AXIS_NOTE_MEDIAN = ("The lines show the typical value (median) of each series, not the "
                    "models' error.")
AXIS_NOTE_ERROR = "The error is shown in the indicators below."
AXIS_LABEL_MARGIN = 6     # close to 0 or 100, the short label goes inside the axis
# figure height (px) and Y axis range (the categories go from 0 to 1; the
# numbers are above 1 and the category names below 0)
WQI_AXIS_HEIGHT = 150
WQI_AXIS_RANGE_Y = [-0.38, 1.22]
# square in the series color before each legend line of the axis
COLOR_SQUARE_FORMAT = ':color[■]{{foreground="{color}"}} {text}'

# (key, title, text, badges, value suffix, decimal places,
#  direction of the better value: 'higher' or 'lower')
METRIC_CARDS = [
    ('R2', "R² (Coefficient of Determination)",
     "How well the model predicts the observed data. 0 or negative = the model does not "
     "predict at all / 1 = perfect prediction. So the closer to 1, the better.",
     ["Range: from 1 down to negative values", "Unit: unitless"], '', DECIMALS_R2, 'higher'),
    ('MAPE', "MAPE (Mean Absolute Percentage Error)",
     "Average error as a percentage. The lower, the better.",
     ["Unit: %"], '%', DECIMALS_MAPE, 'lower'),
    ('MAE', "MAE (Mean Absolute Error)",
     "On average, how many WQI points the model is off by. The lower, the better.",
     ["Unit: WQI points"], '', DECIMALS_WQI, 'lower'),
    ('RMSE', "RMSE (Root Mean Square Error)",
     "Similar to MAE and never smaller than it, but it penalizes large errors much more "
     "heavily. For example, a single sample that is off by 20 WQI points worsens the RMSE "
     "a lot, even if all the others are almost right. The lower, the better.",
     ["Unit: WQI points"], '', DECIMALS_WQI, 'lower'),
]

TITLE_PREDICTED_OBSERVED_LR = "Predicted vs. Observed: Linear Regression"
TITLE_PREDICTED_OBSERVED_DT = "Predicted vs. Observed: Decision Tree"
PREDICTED_OBSERVED_X_AXIS = "Observed WQI"
PREDICTED_OBSERVED_Y_AXIS = "Predicted WQI"
IDEAL_LINE_LEGEND = "Ideal line (y = x)"
HOVER_PREDICTED_OBSERVED = "Observed WQI: %{customdata[0]}<br>Predicted WQI: %{customdata[1]}"
HOVER_IDEAL_LINE = "%{customdata}"

ERROR_BANDS_TITLE = "Absolute Error Bands = |Observed WQI − Predicted WQI|"
ERROR_BANDS_TEXT = (
    "Purpose: when a model is wrong, understand the impact of the error. Example: a model "
    "can be off by 1 point or by 20 points, and if the percentage of LR samples is much "
    "higher than DT's in the last bands (10 to 15 and >15), it means that when LR is "
    "wrong, it produces predictions much further from the observed values than DT, "
    "creating more and worse outliers. This chart is closely connected to RMSE. The lower "
    "the percentage of samples in the last bands, the better."
)
CHART_ERROR_BANDS_X_AXIS = "Absolute error (WQI points)"
CHART_ERROR_BANDS_Y_AXIS = "% of samples"
PCT_SUFFIX = "%"
HOVER_ERROR_BANDS = ("<b>%{customdata[0]}</b><br>Error band: %{customdata[1]}<br>"
                     "%{customdata[2]} of samples<extra></extra>")

# ---------------------------------------------------------------------------
# Texts: Model Predictions
# ---------------------------------------------------------------------------
NAME_LR = 'Linear Regression'
NAME_DT = 'Decision Tree'

SECTION_SCATTER = "LR vs. DT Scatter Plot"
SCATTER_TEXT = (
    "**What it shows:** each point is a sample, placed by the Linear Regression "
    "prediction (horizontal axis) and the Decision Tree prediction (vertical axis). The "
    "dashed line represents perfect agreement between the two models.\n\n"
    "- **Good result:** the points line up close to the dashed line, meaning the models "
    "predicted similar values.\n"
    "- **Bad result:** points scattered far from the line show that the models disagree "
    "on those samples.\n\n"
    "The points form vertical columns because the Linear Regression prediction is "
    "rounded to a whole number.")

# scatter plot labels
CHART_SAMPLES = 'Samples'
CHART_AGREEMENT_LINE = 'Agreement (y = x)'
CHART_SCATTER_TITLE = 'Scatter Plot: Linear Regression vs. Decision Tree'
CHART_AXIS_PREDICTED_LR = 'Predicted WQI (LR)'
CHART_AXIS_PREDICTED_DT = 'Predicted WQI (DT)'
HOVER_SCATTER = "Predicted WQI (LR): %{customdata[0]}<br>Predicted WQI (DT): %{customdata[1]}"

# ---------------------------------------------------------------------------
# Texts: water quality monitoring charts (Overview and Model Predictions)
# ---------------------------------------------------------------------------
_MONITORING_THRESHOLDS_TEXT = (
    "The purpose of this chart is to see on which dates water quality was very low (up "
    "to the lower threshold) or very high (above the upper threshold). The thresholds "
    "were set arbitrarily; the mean line is calculated from the data:\n\n"
    "1. Upper threshold = {upper}, because according to CETESB's water quality "
    "categories, above {upper} the water quality is excellent\n"
    "2. Lower threshold = {lower}, because according to CETESB's water quality "
    "categories, up to {lower} the water quality is poor or very poor\n"
    "3. Mean = average WQI of the selected sampling site\n\n"
    "- **Good result:** few points up to the lower threshold ({lower}) and many above "
    "the upper threshold ({upper}).\n"
    "- **Bad result:** many points up to the lower threshold ({lower}) and few above the "
    "upper threshold ({upper})."
).format(upper=MONITORING_UPPER_THRESHOLD, lower=MONITORING_LOWER_THRESHOLD)
SECTION_MONITORING_PREDICTED = "Water Quality Monitoring Charts (Predicted)"
MONITORING_PREDICTED_TEXT = (
    "**What it shows:** the WQI predicted by each model over time at the selected "
    "sampling site. " + _MONITORING_THRESHOLDS_TEXT)
SECTION_MONITORING_OBSERVED = "Water Quality Monitoring Chart (Observed)"
MONITORING_OBSERVED_TEXT = (
    "**What it shows:** the observed WQI over time at the selected sampling site. "
    + _MONITORING_THRESHOLDS_TEXT)
INFO_MONITORING_MISSING_COLUMNS = ("To see the water quality monitoring chart, include "
                                   "the Sampling Site and Date columns in your spreadsheet.")
SITE_SELECTOR_LABEL = "Sampling Site"

# summary below each chart: {pct} = count / total in %, {word} =
# WORD_SAMPLE_SINGULAR when total == 1, otherwise WORD_SAMPLE_PLURAL
MONITORING_LOW_FORMAT = (":red-background[**{pct}** of samples ({count} of {total} "
                         "{word}) with poor or very poor WQI (up to {lower}).]")
MONITORING_HIGH_FORMAT = (":green-background[**{pct}** of samples ({count} of {total} "
                          "{word}) with excellent WQI (above {upper}).]")
WORD_SAMPLE_SINGULAR = "sample"
WORD_SAMPLE_PLURAL = "samples"

CHART_MONITORING_TITLE = 'WQI Monitoring: {name}'
CHART_OBSERVED_NAME = 'Observed'
CHART_AXIS_DATE = 'Date'
CHART_AXIS_WQI_OBSERVED = 'Observed WQI'
CHART_AXIS_WQI_PREDICTED = 'Predicted WQI'
CHART_MEAN = 'Mean ({v})'
CHART_LOWER_THRESHOLD = 'Lower threshold ({v})'
CHART_UPPER_THRESHOLD = 'Upper threshold ({v})'
CHART_WQI_POOR = 'Poor or very poor WQI'
CHART_WQI_EXCELLENT = 'Excellent WQI'
MONITORING_AXIS_MARGIN = 2     # Y axis margin when a value is outside 0 to 100
HOVER_MONITORING = "Date: %{customdata[0]}<br>WQI: %{customdata[1]}<br>Category: %{customdata[2]}"

# ---------------------------------------------------------------------------
# Texts: Sampling Site Comparison
# ---------------------------------------------------------------------------
SITES_NOTE = ("The R² of a single sampling site is usually lower because the WQI varies "
              "less within it. To compare sampling sites, use MAE.")
SITES_TABLE_COLUMNS = ["Sampling Site", "Samples", "R²", "MAE", "MAPE", "RMSE"]
SITES_HIGHLIGHT_COLUMN = "MAE"    # metric recommended by SITES_NOTE

# ---------------------------------------------------------------------------
# Texts: About the Dashboard
# ---------------------------------------------------------------------------
ABOUT_VARIABLES_TITLE = "Water Quality Variables"
ABOUT_VARIABLES_COLUMNS = ["Abbreviation", "Name", "Unit"]
# own list for the About table (TON and WQI are not among the required rows
# of the template)
ABOUT_VARIABLES = [
    ('BOD', 'Biochemical oxygen demand', 'mg/L'),
    ('THC', 'Thermotolerant coliforms (E. coli)', 'CFU/100 mL'),
    ('TOP', 'Total phosphorus', 'mg/L'),
    ('DOS', 'Dissolved oxygen saturation', '% saturation'),
    ('pH', 'pH', 'unitless'),
    ('TOS', 'Total solids', 'mg/L'),
    ('TUR', 'Turbidity', 'NTU'),
    ('TON', 'Total nitrogen', 'mg/L'),
    ('WQI', 'Water Quality Index (CETESB)', 'unitless'),
]
ABOUT_MODEL_DETAILS_TITLE = "Model Details"
ABOUT_MODEL_DETAILS = [
    "Input variables: {n_variables}",
    "Decision Tree: depth {depth} and {leaves} leaves",
    "Missing values: filled using the {neighbors} nearest neighbors method (KNN), fitted "
    "during training.",
]
ABOUT_CATEGORIES_TITLE = "WQI Categories"
ABOUT_CATEGORIES_COLUMNS = ["Category", "WQI range"]

# ---------------------------------------------------------------------------
# Exported Excel file
# ---------------------------------------------------------------------------
SHEET_SUMMARY = 'Summary'
SHEET_PREDICTIONS = 'Predictions'
SHEET_METRICS = 'Metrics'
SHEET_SITES = 'Sampling Sites'          # Excel accepts at most 31 characters
SHEET_REMOVED = 'Removed Rows'
SHEET_ADJUSTMENTS = 'Automatic Adjustments'
SHEET_WARNINGS = 'Warnings'
TEMPLATE_SHEET_DATA = 'Data'
TEMPLATE_SHEET_DICTIONARY = 'Dictionary'

SUMMARY_COLUMNS = ['Item', 'Value']
GENERATED_AT_FORMAT = '%Y-%m-%d %H:%M'  # "Generated at (UTC)", time in UTC
EXCEL_DATE_FORMAT = 'YYYY-MM-DD'        # number_format of the Date column in Predictions

# headers of the Predictions and Removed Rows sheets (the internal keys stay
# in the code; only the Excel writing uses these names)
EXCEL_COLUMN_ROW = 'Original row'
EXCEL_COLUMN_REASON = 'Reason'
EXCEL_PREDICTION_COLUMNS = {
    'Original_row': EXCEL_COLUMN_ROW,
    DATE_COLUMN: 'Date',
    SITE_COLUMN: 'Sampling Site',
    'WQI_observed': 'Observed WQI',
    'Prediction_LR': 'LR prediction',
    'Prediction_DT': 'DT prediction',
}
USED_IN_MODEL_FORMAT = "{abbreviation} (used in the model)"

EXCEL_METRICS_COLUMNS = ['Indicator', 'Linear Regression', 'Decision Tree', 'Unit']
EXCEL_METRICS_ROWS = [
    ('R2', 'R²', 'unitless'),
    ('MAPE', 'MAPE (%)', '%'),
    ('MAE', 'MAE', 'WQI points'),
    ('RMSE', 'RMSE', 'WQI points'),
]
EXCEL_ERROR_BANDS_UNIT = '%'    # rows of the error bands (labels in ERROR_BANDS)
EXCEL_SITES_COLUMNS = ['Sampling Site', 'Samples', 'R² LR', 'R² DT', 'MAE LR', 'MAE DT',
                       'MAPE LR', 'MAPE DT', 'RMSE LR', 'RMSE DT']
EXCEL_WARNINGS_COLUMNS = ['Warning', 'Number of rows', EXCEL_COLUMN_ROW]
EXCEL_COLUMN_ADJUSTMENT = 'Adjustment'
EXCEL_ADJUSTMENTS_COLUMNS = [EXCEL_COLUMN_ROW, 'Variable', EXCEL_COLUMN_ADJUSTMENT,
                             'Original value', 'Value used by the model']
TEMPLATE_DICTIONARY_COLUMNS = ['Column', 'Name', 'Unit', 'Required', 'Also accepted as']

ADJUSTMENT_IMPUTATION = 'Empty cell filled (KNN, 5 neighbors)'
ADJUSTMENT_WINSORIZATION = 'Extreme value adjusted (10% winsorization)'
REASON_ABOVE = '{var} above {maximum}'
REASON_BELOW = '{var} below {minimum}'

SUMMARY_ITEMS = {
    'file': 'File',
    'generated_at': 'Generated at (UTC)',
    'status': 'Status',
    'rows_read': 'Rows read',
    'rows_removed': 'Rows removed by the filter',
    'pct_removed': 'Rows removed by the filter (%)',
    'rows_predicted': 'Rows predicted',
    'rows_wqi_observed': 'Rows with a valid observed WQI',
    'cells_imputed': 'Empty cells filled',
    'values_winsorized': 'Extreme values adjusted',
}
STATUS_OK = 'Processed'
STATUS_BLOCKED = 'Blocked: {reason}'

WARNING_WQI_ZERO = "{n} rows with an observed WQI equal to 0 were excluded from MAPE only"
WARNING_NO_WQI = ("{n} rows without a valid observed WQI have predictions, but are excluded "
                  "from the metrics, the Predicted vs. Observed charts, the monitoring chart "
                  "(Observed) and the sampling site comparison")
WARNING_NON_NUMERIC = ("{n} cells with text instead of a number in {column} were treated as "
                       "empty. Use a period as the decimal separator (e.g., 2.5) and no "
                       "thousands separator.")
WARNING_EMPTY_SITE = ("{n} rows with an empty Sampling Site were excluded from the sampling "
                      "site comparison and the monitoring charts")
WARNING_DUPLICATE_COLUMN = ("The variable {abbreviation} appears in two columns ({col1} and "
                            "{col2}). Column {col1} was used.")
WARNING_INVALID_DATE = ("{n} rows with a date that could not be read were excluded from the "
                        "monitoring charts")
WARNING_NO_DATE = ("The spreadsheet has no date column, so the monitoring charts are not "
                   "generated")
WARNING_HIGH_REMOVAL = ("More than 80% of the rows were removed. Check that the column units "
                        "match the template.")

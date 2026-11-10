# Water Quality Dashboard (WQI)

A Streamlit dashboard that predicts the **Water Quality Index (WQI)** with two
machine learning models and compares the predictions with the observed WQI.

You upload a spreadsheet with water quality measurements and the dashboard shows:

- how large each model's errors are (R², MAE, MAPE, RMSE and absolute error bands);
- how the two models compare with each other (Predicted vs. Observed charts and an
  LR vs. DT scatter plot);
- if the spreadsheet has a `Sampling Site` column, how the results vary across
  sampling sites, including water quality monitoring charts over time (these also
  need a `Date` column).

Results can be exported to an Excel file (`Export results (.xlsx)`).

## Models and variables

Two models trained beforehand are used:

- **Linear Regression (LR)**: its prediction is rounded to a whole number.
- **Decision Tree (DT)**.

Both models use the same 7 input variables. TON is used only in the data quality
filter, and WQI only to measure the error of the predictions.

| Abbreviation | Name | Unit |
|---|---|---|
| BOD | Biochemical oxygen demand | mg/L |
| THC | Thermotolerant coliforms (E. coli) | CFU/100 mL |
| TOP | Total phosphorus | mg/L |
| DOS | Dissolved oxygen saturation | % saturation |
| pH | pH | unitless |
| TOS | Total solids | mg/L |
| TUR | Turbidity | NTU |
| TON | Total nitrogen | mg/L |
| WQI | Water Quality Index (CETESB) | unitless |

### Prediction pipeline

For each uploaded spreadsheet the dashboard:

1. removes the rows with values outside the range used to train the models
   (data quality filter: pH from 2 to 12; BOD up to 30; DOS up to 140; TOS up to 500;
   TUR up to 100; TON up to 100; TOP up to 10);
2. removes TON and WQI from the model input and puts the variables in the fixed
   order BOD, THC, TOP, DOS, PH, TOS, TUR;
3. fills empty cells with the KNN imputer fitted during training (`imputer.transform`);
4. adjusts extreme values with a 10% winsorization on each side;
5. scales the variables with the scaler fitted during training (`scaler.transform`);
6. predicts with both models (`predict`); the Linear Regression prediction is rounded
   with `np.round`.

**The training artifacts (`*.pk` files) are only used with `.transform()` and
`.predict()`. They are never refitted (`fit()` / `fit_transform()`) or recreated.**
This guarantees that the dashboard reproduces exactly the preprocessing of the
training.

## Files

| File | Purpose |
|---|---|
| `app.py` | Streamlit interface (screens and charts). |
| `config.py` | All texts, labels, limits, colors and formats used by the app. |
| `processing.py` | Reading of the spreadsheet, prediction pipeline and Excel files (template and exported results). |
| `metrics.py` | Error metrics, error bands, sampling site table and number formatting. |
| `linear_regression_model.pk` | Trained Linear Regression model. |
| `decision_tree_model.pk` | Trained Decision Tree model. |
| `scaler.pk` | Scaler fitted during training. |
| `knn_imputer.pk` | KNN imputer (5 neighbors) fitted during training. |
| `model_info.json` | Reference numbers of the trained models (used by the tests). |
| `UGRHI23_example.xlsx` | Example dataset (button `Use example dataset`). |
| `prepare_example_dataset.py` | Script that built the example dataset from the original CETESB file. |
| `requirements.txt` | Python packages and versions. |
| `.streamlit/config.toml` | Streamlit theme (colors). |
| `tests/` | Automated tests (`pytest`), with test files in `tests/fixtures/` and reference results in `tests/golden/`. |

## How to install and run

Requires Python 3.13 (the version used to develop the dashboard).

```bash
pip install -r requirements.txt
streamlit run app.py
```

The dashboard opens in the browser. To run the tests:

```bash
python -m pytest
```

## Spreadsheet format

Accepted formats: `.xlsx`, `.xls` or `.csv`. Click `Download template` in the
dashboard to get a template (`wqi_template.xlsx`) with all the columns and a
dictionary sheet.

**Columns**

- Required: `BOD`, `THC`, `TOP`, `DOS`, `PH` (or `pH`), `TOS`, `TUR`.
- Optional: `TON`, `WQI` (observed WQI, needed to measure the errors),
  `Sampling Site` and `Date`.
- Headers are case-insensitive. Only the English abbreviations above are accepted.
- A unit may be written in the header, between parentheses or square brackets,
  e.g. `BOD (mg/L)`. Accepted units (compared without spaces, case-insensitive):

  | Variable | Accepted units |
  |---|---|
  | BOD, TOP, TOS, TON | `mg/L` |
  | THC | `CFU/100 mL`, `MPN/100 mL`, `CFU/100`, `MPN/100` |
  | DOS | `%`, `% sat`, `% saturation` |
  | TUR | `NTU` |
  | PH, WQI | empty, `unitless` or `-` |

  Any other unit blocks the processing, so that values in the wrong unit are never
  used by the models.
- `Sampling Site` is also accepted as `Site`, `Sampling Point`, `Station` or `UGRHI`
  (if there is more than one, this is the order of priority).
- `Date` is also accepted as `Sampling Date`, `Collection Date` or `Sample Date`.

**Numbers**: use a period as the decimal separator (e.g. `2.5`) and no thousands
separator. A cell with text instead of a number (e.g. `2,5`) is treated as empty
and listed in the warnings. In CSV files the decimal separator is always the period,
whatever the column separator (`,`, `;` or tab).

**Dates**: real Excel dates, or text in the `dd/mm/yyyy` or `yyyy-mm-dd` format
(e.g. `13/02/2023` or `2023-02-13`). Dates that cannot be read are listed in the
warnings and left out of the monitoring charts.

**Empty cells and extreme values**: empty cells in the variables are filled and
extreme values are adjusted using the models' method (see the pipeline above).
Every change is listed in the `Automatic Adjustments` sheet of the exported Excel file.

## Example dataset

`UGRHI23_example.xlsx` (2,097 rows) comes from the CETESB 2023 water quality
dataset (UGRHI23), with measurements from the 22 Water Resources Management
Units (UGRHI) of the State of Sao Paulo, Brazil. The `Sampling Site` column joins
the UGRHI number with the name of the basin (e.g. `5 Piracicaba/Capivari/Jundiaí`);
basin names are proper names and are kept in Portuguese. The
`prepare_example_dataset.py` script documents how the file was built from the
original CETESB spreadsheet (which is not included in this repository).

WQI categories (source: CETESB, 2023):

| Category | WQI range |
|---|---|
| Very poor | up to 19 |
| Poor | above 19 up to 36 |
| Fair | above 36 up to 51 |
| Good | above 51 up to 79 |
| Excellent | above 79 up to 100 |

## License

MIT License.

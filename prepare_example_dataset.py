"""
Builds the example dataset of the dashboard (UGRHI23_example.xlsx) from the
original CETESB data (UGRHI23.xlsx, CETESB 2023), which is NOT changed. The
original file is not included in this repository.

What changes compared with the original:
  * the "Ponto" column (station code) is removed;
  * the "UGRHI" column (code from 1 to 22) is replaced by the column
    "Sampling Site", in the same position, with the text "<code> <basin name>"
    (e.g. "6 Alto Tietê"), using Table 9.1 of CETESB 2023. The basin names
    are proper names and stay in Portuguese;
  * the "Data da Coleta" column is renamed to "Date" and shown in the
    yyyy-mm-dd format (the values are real Excel dates).
All other columns and all rows stay the same.

How to run (in the wqi_en folder, with UGRHI23.xlsx in the same folder):
    C:\\v\\Scripts\\python.exe prepare_example_dataset.py
"""
import os

import openpyxl
import pandas as pd

FOLDER = os.path.dirname(os.path.abspath(__file__))
ORIGINAL = os.path.join(FOLDER, 'UGRHI23.xlsx')
OUTPUT = os.path.join(FOLDER, 'UGRHI23_example.xlsx')

# Water Resources Management Units (UGRHI), CETESB 2023, Table 9.1
UGRHI_NAMES = {
    1: 'Mantiqueira',
    2: 'Paraíba do Sul',
    3: 'Litoral Norte',
    4: 'Pardo',
    5: 'Piracicaba/Capivari/Jundiaí',
    6: 'Alto Tietê',
    7: 'Baixada Santista',
    8: 'Sapucaí/Grande',
    9: 'Mogi-Guaçu',
    10: 'Sorocaba/Médio Tietê',
    11: 'Ribeira do Iguape/Litoral Sul',
    12: 'Baixo Pardo/Grande',
    13: 'Tietê/Jacaré',
    14: 'Alto Paranapanema',
    15: 'Turvo/Grande',
    16: 'Tietê/Batalha',
    17: 'Médio Paranapanema',
    18: 'São José dos Dourados',
    19: 'Baixo Tietê',
    20: 'Aguapeí',
    21: 'Peixe',
    22: 'Pontal do Paranapanema',
}

# column names of the original CETESB file -> names in the example dataset
ORIGINAL_UGRHI_COLUMN = 'UGRHI'
ORIGINAL_STATION_COLUMN = 'Ponto'
ORIGINAL_DATE_COLUMN = 'Data da Coleta'
SITE_COLUMN = 'Sampling Site'
DATE_COLUMN = 'Date'
DATE_DISPLAY_FORMAT = 'yyyy-mm-dd'


def build(original=ORIGINAL, output=OUTPUT):
    data = pd.read_excel(original)

    # UGRHI code -> "<code> <name>" (stops if a code is not in the table)
    codes = data[ORIGINAL_UGRHI_COLUMN].astype(int)
    unknown = sorted(set(codes) - set(UGRHI_NAMES))
    if unknown:
        raise ValueError(f'UGRHI not in Table 9.1: {unknown}')
    site = codes.map(lambda c: f'{c} {UGRHI_NAMES[c]}')

    position = data.columns.get_loc(ORIGINAL_UGRHI_COLUMN)
    example = data.drop(columns=[ORIGINAL_UGRHI_COLUMN, ORIGINAL_STATION_COLUMN])
    example.insert(position, SITE_COLUMN, site)
    example = example.rename(columns={ORIGINAL_DATE_COLUMN: DATE_COLUMN})
    example.to_excel(output, index=False)

    # dates shown as yyyy-mm-dd (the cells stay real Excel dates)
    workbook = openpyxl.load_workbook(output)
    sheet = workbook.active
    date_col = list(example.columns).index(DATE_COLUMN) + 1
    for (cell,) in sheet.iter_rows(min_row=2, min_col=date_col, max_col=date_col):
        cell.number_format = DATE_DISPLAY_FORMAT
    workbook.save(output)

    # check
    read_back = pd.read_excel(output)
    print(f'{output}: {len(read_back)} rows, '
          f'{read_back[SITE_COLUMN].nunique()} distinct values of Sampling Site')
    print('columns:', list(read_back.columns))


if __name__ == '__main__':
    build()

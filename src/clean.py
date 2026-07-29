"""Data cleaning utilities

Implement cleaning / ETL steps that transform raw inputs into data/processed/ files.
"""
import os
import pandas as pd

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
RAW = os.path.join(ROOT, 'data', 'raw')
PROCESSED = os.path.join(ROOT, 'data', 'processed')


def clean_all():
    os.makedirs(PROCESSED, exist_ok=True)
    # Add cleaning logic here. Example (pseudocode):
    # df = pd.read_csv(os.path.join(RAW, 'prices.csv'))
    # df_clean = some_cleaning(df)
    # df_clean.to_csv(os.path.join(PROCESSED, 'prices_clean.csv'), index=False)
    print('Cleaning pipeline not yet implemented. Add your ETL steps in src/clean.py')


if __name__ == '__main__':
    clean_all()

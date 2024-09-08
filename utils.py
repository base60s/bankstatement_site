import pandas as pd

def merge_dataframes(dataframes):
    return pd.concat(dataframes, ignore_index=True)

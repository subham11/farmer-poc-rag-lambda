import pandas as pd

def load_local_dataset(path="data/farmer_dataset.csv"):
    return pd.read_csv(path)

import pandas as pd
import numpy as np
import json, os

def num(x):
    try:
        return float(str(x).replace(',', '.'))
    except Exception:
        try:
            return float(x)
        except Exception:
            return 0.0

def read_excel_any(file, sheet=None):
    if sheet is None:
        return pd.read_excel(file)
    return pd.read_excel(file, sheet_name=sheet)

def load_config(path='storage/config.json'):
    if os.path.exists(path):
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)
    # padrão sensato
    return {
        "delivery_mode": "Entrega própria",
        "taxa_ifood_pct": 0.23,
        "custo_entrega_propria": 8.0
    }

def save_config(cfg, path='storage/config.json'):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(cfg, f, ensure_ascii=False, indent=2)

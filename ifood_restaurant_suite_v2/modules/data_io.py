# modules/data_io.py
from __future__ import annotations
import io
import json
from pathlib import Path
from typing import Optional, Dict, Any, Tuple

import pandas as pd

# Raiz do projeto (pasta que contém app.py)
ROOT_DIR = Path(__file__).resolve().parents[1]
ASSETS_DIR = ROOT_DIR / "assets"
STORAGE_DIR = ROOT_DIR / "storage"
TEMPLATES_DIR = ROOT_DIR / "templates"

ASSETS_DIR.mkdir(exist_ok=True)
STORAGE_DIR.mkdir(exist_ok=True)
TEMPLATES_DIR.mkdir(exist_ok=True)


# -------------------------
# Utilidades de arquivos
# -------------------------
def read_json(path: Path) -> Dict[str, Any]:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def write_json(path: Path, data: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def load_asset_json(name: str) -> Optional[Dict[str, Any]]:
    path = ASSETS_DIR / name
    if path.exists():
        return read_json(path)
    return None


def save_storage_json(name: str, data: Dict[str, Any]) -> None:
    write_json(STORAGE_DIR / name, data)


def load_storage_json(name: str, default: Optional[Dict[str, Any]] = None) -> Optional[Dict[str, Any]]:
    path = STORAGE_DIR / name
    if path.exists():
        return read_json(path)
    return default


# -------------------------
# Leitura de planilhas (.xlsx)
# -------------------------
def read_xlsx(stream_or_path: io.BytesIO | Path, sheet: Optional[str | int] = None) -> pd.DataFrame:
    """
    Lê um Excel em DataFrame. Aceita arquivo enviado via Streamlit (uploader) ou Path local.
    """
    if isinstance(stream_or_path, Path):
        return pd.read_excel(stream_or_path, sheet_name=sheet, engine="openpyxl")
    # bytes (uploader)
    return pd.read_excel(stream_or_path, sheet_name=sheet, engine="openpyxl")


def safe_read_xlsx(stream_or_path: io.BytesIO | Path | None, sheet: Optional[str | int] = None) -> pd.DataFrame:
    if stream_or_path is None:
        return pd.DataFrame()
    try:
        return read_xlsx(stream_or_path, sheet=sheet)
    except Exception:
        return pd.DataFrame()


# -------------------------
# Conveniências para o app
# -------------------------
def guide_paths() -> Dict[str, str]:
    """
    Retorna um guia (se existir) de onde baixar relatórios no portal.
    Cai para um guia mínimo se o arquivo não existir.
    """
    guide = load_asset_json("data_guide.json")
    if guide:
        return guide

    # fallback minimalista
    return {
        "pedidos": "Relatórios → Pedidos → Exportar (XLSX)",
        "conciliacao": "Financeiro → Conciliação → Exportar (XLSX)",
        "vendas": "Relatórios → Vendas → Exportar (XLSX)",
        "operacao": "Relatórios → Operação → Exportar (XLSX)",
        "cardapio": "Cardápios → Exportar (XLSX) ou relatórios de funil/itens",
        "ficha_tecnica_modelo": "templates/ficha_tecnica_exemplo.csv",
    }


def parse_uploaded_files(files: Dict[str, io.BytesIO | None]) -> Dict[str, pd.DataFrame]:
    """
    Recebe um dicionário com chaves ('pedidos','conciliacao','vendas','operacao','cardapio')
    e valores sendo bytes de upload; devolve DataFrames.
    """
    out: Dict[str, pd.DataFrame] = {}
    for k, blob in files.items():
        out[k] = safe_read_xlsx(blob)
    return out


def slugify(text: str) -> str:
    return (
        text.lower()
        .replace(" ", "_")
        .replace("/", "_")
        .replace("\\", "_")
        .replace("'", "")
        .replace('"', "")
    )

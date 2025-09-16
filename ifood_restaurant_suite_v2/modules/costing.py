# modules/costing.py
from __future__ import annotations
from typing import Dict, List, Tuple
import pandas as pd


def custo_produto(insumos: Dict[str, Dict], ficha: List[Tuple[str, float]]) -> float:
    """
    Calcula custo de um produto: soma(qtd * custo_unit) dos insumos.
    ficha: lista de (nome_insumo, quantidade)
    """
    total = 0.0
    for nome, qtd in ficha:
        meta = insumos.get(nome)
        if meta is None:
            continue
        total += float(qtd) * float(meta.get("custo", 0))
    return total


def margem_liquida(preco_venda: float, custo_prod: float, taxa_ifood: float) -> float:
    """
    Margem líquida aproximada por item: venda - (custo + taxa_ifood * venda)
    """
    return float(preco_venda) - (float(custo_prod) + float(taxa_ifood) * float(preco_venda))


def tabela_precificacao(
    fichas: Dict[str, List[Tuple[str, float]]],
    insumos: Dict[str, Dict],
    precos: Dict[str, float],
    taxa_ifood: float,
) -> pd.DataFrame:
    """
    Monta uma tabela com custo, taxa e margem por produto.
    """
    rows = []
    for produto, composicao in fichas.items():
        pv = float(precos.get(produto, 0))
        cp = custo_produto(insumos, composicao)
        taxa = pv * taxa_ifood
        ml = margem_liquida(pv, cp, taxa_ifood)
        rows.append(
            {
                "produto": produto,
                "preco_venda": round(pv, 2),
                "custo_produto": round(cp, 2),
                "taxa_ifood": round(taxa, 2),
                "margem_liquida": round(ml, 2),
                "margem_%": round((ml / pv) * 100, 2) if pv > 0 else 0.0,
            }
        )
    if not rows:
        return pd.DataFrame(columns=["produto", "preco_venda", "custo_produto", "taxa_ifood", "margem_liquida", "margem_%"])
    return pd.DataFrame(rows).sort_values("margem_liquida", ascending=True).reset_index(drop=True)

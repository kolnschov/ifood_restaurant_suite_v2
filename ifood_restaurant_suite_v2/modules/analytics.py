# modules/analytics.py
from __future__ import annotations
import pandas as pd
from typing import Dict


def kpis_basicos(dfs: Dict[str, pd.DataFrame]) -> pd.DataFrame:
    """
    KPIs simplificados: pedidos, ticket médio, % incentivos (se existir coluna),
    tudo com defesas para DataFrames vazios.
    """
    pedidos = dfs.get("pedidos", pd.DataFrame())
    vendas = dfs.get("vendas", pd.DataFrame())

    total_pedidos = len(pedidos) if not pedidos.empty else 0

    # ticket médio: se tiver 'valor_bruto' e 'id_pedido'
    ticket = 0.0
    if not vendas.empty:
        col_valor = None
        for c in vendas.columns:
            if "valor" in c.lower() and "bruto" in c.lower():
                col_valor = c
                break
        if col_valor:
            total_venda = vendas[col_valor].fillna(0).sum()
            qtd = len(vendas)
            ticket = float(total_venda / qtd) if qtd > 0 else 0.0

    # % incentivos: procura colunas plausíveis
    incentivo_perc = 0.0
    if not vendas.empty:
        valor_col = None
        desc_col = None
        for c in vendas.columns:
            cl = c.lower()
            if ("valor" in cl and "bruto" in cl) or ("total" in cl and "bruto" in cl):
                valor_col = c
            if "desconto" in cl or "cupom" in cl:
                desc_col = c
        if valor_col and desc_col:
            bruto = vendas[valor_col].fillna(0).sum()
            desc = vendas[desc_col].fillna(0).sum()
            incentivo_perc = float(desc / bruto) if bruto > 0 else 0.0

    return pd.DataFrame(
        {
            "KPI": ["Pedidos", "Ticket médio", "% incentivo em vendas"],
            "Valor": [total_pedidos, round(ticket, 2), round(incentivo_perc * 100, 2)],
            "Unidade": ["un", "R$", "%"],
        }
    )


def produtos_topo(dfs: Dict[str, pd.DataFrame], top_n: int = 10) -> pd.DataFrame:
    """
    Retorna top produtos por quantidade em 'vendas' se houver colunas compatíveis.
    """
    vendas = dfs.get("vendas", pd.DataFrame())
    if vendas.empty:
        return pd.DataFrame(columns=["produto", "qtd"])
    # heurística de colunas
    prod_col = None
    qtd_col = None
    for c in vendas.columns:
        cl = c.lower()
        if prod_col is None and ("produto" in cl or "item" in cl):
            prod_col = c
        if qtd_col is None and ("qtd" in cl or "quantidade" in cl):
            qtd_col = c
    if not prod_col or not qtd_col:
        return pd.DataFrame(columns=["produto", "qtd"])

    df = (
        vendas[[prod_col, qtd_col]]
        .rename(columns={prod_col: "produto", qtd_col: "qtd"})
        .groupby("produto", as_index=False)["qtd"]
        .sum()
        .sort_values("qtd", ascending=False)
        .head(top_n)
    )
    return df.reset_index(drop=True)

# modules/assistant.py
from __future__ import annotations
from typing import Dict
import pandas as pd


def recomendacoes_basicas(tabela_precos: pd.DataFrame) -> Dict[str, str]:
    """
    Gera dicas simples a partir da tabela de precificação (margens).
    """
    tips = []

    if tabela_precos.empty:
        return {"resumo": "Cadastre insumos, monte a composição e informe preço de venda para receber recomendações."}

    # 1) Produtos no vermelho
    negativos = tabela_precos[tabela_precos["margem_liquida"] < 0]
    if not negativos.empty:
        nomes = ", ".join(negativos["produto"].head(5).tolist())
        tips.append(f"Produtos no prejuízo: {nomes}. Revise preço, taxa aplicada e gramagens.")

    # 2) Produtos com margem % baixa
    baixos = tabela_precos[tabela_precos["margem_%"] < 15]
    if not baixos.empty:
        nomes = ", ".join(baixos["produto"].head(5).tolist())
        tips.append(f"Margem abaixo de 15% em: {nomes}. Avalie reajuste de preço ou reengenharia de ficha técnica.")

    # 3) Top margem (sugestão de destaque)
    tops = tabela_precos.sort_values("margem_%", ascending=False).head(3)
    if not tops.empty:
        nomes = ", ".join(tops["produto"].tolist())
        tips.append(f"Destaque em anúncios e combos: {nomes} (maiores margens).")

    if not tips:
        tips.append("Estrutura saudável. Siga monitorando incentivos, ticket e custos fixos mensais.")

    return {"resumo": " • ".join(tips)}

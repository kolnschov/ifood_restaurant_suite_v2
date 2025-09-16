import pandas as pd
import numpy as np

# Calcula custo total e margens a partir da ficha técnica (formato editor/import)
def compute_costs(df_ficha):
    if len(df_ficha) == 0:
        return pd.DataFrame()
    df = df_ficha.copy()
    if "preco_venda" not in df.columns and "preco_venda_atual" in df.columns:
        df = df.rename(columns={"preco_venda_atual":"preco_venda"})
    df["custo_total_insumo"] = pd.to_numeric(df["quantidade"], errors="coerce").fillna(0) * \
                               pd.to_numeric(df["custo_unitario"], errors="coerce").fillna(0)
    tabela = df.groupby("produto").agg(
        preco_venda=("preco_venda", "max"),
        custo_receita=("custo_total_insumo", "sum")
    ).reset_index()
    tabela["margem_bruta_R$"] = tabela["preco_venda"] - tabela["custo_receita"]
    tabela["margem_bruta_%"] = np.where(
        tabela["preco_venda"] > 0, tabela["margem_bruta_R$"] / tabela["preco_venda"], 0.0
    )
    return tabela


def _receita_liquida(preco, desconto, delivery_mode, taxa_ifood_pct, custo_entrega):
    """
    Receita líquida aproximada recebida pela loja após taxa (ou custo de entrega própria),
    já descontando o cupom/desconto médio por produto.
    """
    pv_eff = max(0.0, float(preco) - float(desconto))
    if delivery_mode == "Entrega pelo iFood (Logística)":
        return pv_eff * (1.0 - float(taxa_ifood_pct))
    else:
        return pv_eff - float(custo_entrega)


# Precificação completa a partir do cadastro guiado
def summarize_pricing(
    ficha_df: pd.DataFrame,
    custos_fixos: dict,
    volume_por_produto: dict,
    impostos_pct: float,
    custo_embalagem: float,
    delivery_mode: str,
    taxa_ifood_pct: float,
    custo_entrega: float,
    margem_alvo_pct: float,
    # NOVO: desconto médio por produto (R$)
    desconto_medio_por_produto: dict | None = None
):
    """
    Consolida custos por produto, rateia fixos por volume e calcula:
      - custo_variavel (insumos + embalagem)
      - custo_fixo_unit (rateio fixos por volume)
      - custo_total_unit = variavel + fixo + impostos + logística (aprox.)
      - margem_liq_atual sem cupom e com cupom (usando desconto_medio_por_produto)
      - preço_sugerido para atingir margem alvo (sem cupom)
    """
    if ficha_df is None or len(ficha_df)==0:
        return pd.DataFrame()

    desconto_medio_por_produto = desconto_medio_por_produto or {}

    d = ficha_df.copy()
    for c in ["quantidade","custo_unitario","preco_venda_atual"]:
        d[c] = pd.to_numeric(d[c], errors="coerce").fillna(0.0)
    d["custo_insumo"] = d["quantidade"] * d["custo_unitario"]

    base = d.groupby("produto").agg(
        preco_venda_atual=("preco_venda_atual","max"),
        custo_insumos=("custo_insumo","sum")
    ).reset_index()

    # volume para rateio
    vol = {p: max(1, int(volume_por_produto.get(p,0))) for p in base["produto"].tolist()}
    vol_total = sum(vol.values()) if sum(vol.values())>0 else 1

    # custo fixo total
    fixo_total = float(sum(custos_fixos.values()))
    base["rateio_fixo_mensal"] = base["produto"].map(lambda p: fixo_total * (vol.get(p,0)/max(1,vol_total)))
    base["custo_fixo_unit"] = base.apply(lambda r: (r["rateio_fixo_mensal"]/max(1,vol.get(r["produto"],1))), axis=1)

    # custo variável
    base["custo_variavel"] = base["custo_insumos"] + float(custo_embalagem)

    # impostos sobre preço
    base["impostos_R$"] = base["preco_venda_atual"] * float(impostos_pct)

    # logística/taxa
    if delivery_mode == "Entrega pelo iFood (Logística)":
        base["taxa_logistica_R$"] = base["preco_venda_atual"] * float(taxa_ifood_pct)
        denom = (1 - float(impostos_pct) - float(taxa_ifood_pct) - float(margem_alvo_pct))
        denom = denom if abs(denom) > 1e-9 else 1e-9
        base["preco_sugerido"] = (base["custo_variavel"] + base["custo_fixo_unit"]) / denom
    else:
        base["taxa_logistica_R$"] = float(custo_entrega)
        denom = (1 - float(impostos_pct) - float(margem_alvo_pct))
        denom = denom if abs(denom) > 1e-9 else 1e-9
        base["preco_sugerido"] = (base["custo_variavel"] + base["custo_fixo_unit"] + float(custo_entrega)) / denom

    # custo total unitário (modelo aproximado "de cima para baixo")
    base["custo_total_unit"] = base["custo_variavel"] + base["custo_fixo_unit"] + base["impostos_R$"] + base["taxa_logistica_R$"]

    # margens com preço atual (sem e com cupom médio)
    base["desconto_medio_R$"] = base["produto"].map(lambda p: float(desconto_medio_por_produto.get(p, 0.0)))

    rec_sem_cupom = base.apply(
        lambda r: _receita_liquida(r["preco_venda_atual"], 0.0, delivery_mode, taxa_ifood_pct, custo_entrega), axis=1
    )
    rec_com_cupom = base.apply(
        lambda r: _receita_liquida(r["preco_venda_atual"], r["desconto_medio_R$"], delivery_mode, taxa_ifood_pct, custo_entrega), axis=1
    )

    # margem líquida "contábil" usando custo_total_unit (aprox.)
    base["margem_liq_R$_sem_cupom"] = rec_sem_cupom - (base["custo_variavel"] + base["custo_fixo_unit"] + base["impostos_R$"] + (0 if delivery_mode=="Entrega pelo iFood (Logística)" else 0))
    base["margem_liq_R$_com_cupom"] = rec_com_cupom - (base["custo_variavel"] + base["custo_fixo_unit"] + base["impostos_R$"] + (0 if delivery_mode=="Entrega pelo iFood (Logística)" else 0))

    base["margem_liq_%_sem_cupom"] = np.where(base["preco_venda_atual"]>0, base["margem_liq_R$_sem_cupom"]/base["preco_venda_atual"], 0.0)
    base["margem_liq_%_com_cupom"] = np.where(base["preco_venda_atual"]>0, base["margem_liq_R$_com_cupom"]/base["preco_venda_atual"], 0.0)

    base["ajuste_R$"] = base["preco_sugerido"] - base["preco_venda_atual"]

    cols = [
        "produto","preco_venda_atual","desconto_medio_R$","preco_sugerido","ajuste_R$",
        "custo_insumos","custo_variavel","custo_fixo_unit","impostos_R$","taxa_logistica_R$",
        "custo_total_unit","margem_liq_R$_sem_cupom","margem_liq_%_sem_cupom",
        "margem_liq_R$_com_cupom","margem_liq_%_com_cupom"
    ]
    return base[cols].sort_values("margem_liq_R$_com_cupom")

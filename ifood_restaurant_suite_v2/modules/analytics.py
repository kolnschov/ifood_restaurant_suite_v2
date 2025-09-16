import pandas as pd

# KPIs básicos do relatório de pedidos
def kpis_pedidos(df_ped):
    out = {}
    out["pedidos_total"] = len(df_ped)
    if "Valor Total" in df_ped.columns:
        out["faturamento_bruto"] = df_ped["Valor Total"].sum()
        out["ticket_medio"] = df_ped["Valor Total"].mean()
    return pd.DataFrame([out])

# Incentivos (origem: iFood ou loja)
def incentivos_por_origem(df_ped):
    if "Incentivo (R$)" not in df_ped.columns:
        return pd.DataFrame()
    if "Origem do Incentivo" not in df_ped.columns:
        return pd.DataFrame()
    return df_ped.groupby("Origem do Incentivo")["Incentivo (R$)"].sum().reset_index()

# Dependência por produto (usando Cardápio/Funil)
def dependencia_por_produto(df_itens):
    if "Produto" not in df_itens.columns or "Pedidos com Promoção" not in df_itens.columns:
        return None, None, None, None
    
    df = df_itens.copy()
    df["%_com_promo"] = df["Pedidos com Promoção"] / df["Pedidos"] * 100
    top_dep = df.sort_values("%_com_promo", ascending=False).head(10)
    top_ind = df.sort_values("%_com_promo").head(10)
    eq = df[(df["%_com_promo"] > 30) & (df["%_com_promo"] < 70)]
    return df, top_dep, top_ind, eq

# Margem líquida aproximada após taxa/custo
def margem_pos_taxa(preco, custo_receita, modo, taxa_ifood, custo_entrega):
    if preco <= 0:
        return 0.0
    if modo == "Entrega pelo iFood (Logística)":
        return preco * (1 - taxa_ifood) - custo_receita
    else:
        return preco - custo_receita - custo_entrega

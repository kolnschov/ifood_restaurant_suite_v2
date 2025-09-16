def advice(product_df, cost_df):
    """
    Gera uma lista de recomendações cruzando dependência de promoção (cardápio/funil)
    e margens (ficha técnica). Mantenho regras simples e objetivas para virar ação.
    """
    tips = []

    # 1) Itens que dependem demais de promoção (se temos cardápio/funil)
    if product_df is not None and len(product_df):
        try:
            dep_col = "%_com_promo"
            prod_col = "Produto" if "Produto" in product_df.columns else "produto"
            dep_sorted = product_df.sort_values(dep_col, ascending=False)
            for _, r in dep_sorted.head(10).iterrows():
                dep_pct = r.get(dep_col, 0)
                p = str(r.get(prod_col, "ITEM"))
                if dep_pct >= 70:
                    tips.append(f"Cortar/segmentar promo de '{p}' (dependência {dep_pct:.1f}%).")
                elif dep_pct >= 50:
                    tips.append(f"Reduzir agressividade da promo de '{p}' (dependência {dep_pct:.1f}%).")
        except Exception:
            # Se o layout do arquivo não bateu, seguimos sem travar
            pass

    # 2) Itens saudáveis (vendem sem cupom)
    if product_df is not None and len(product_df):
        try:
            dep_col = "%_com_promo"
            prod_col = "Produto" if "Produto" in product_df.columns else "produto"
            healthy = product_df.sort_values(dep_col).head(10)
            for _, r in healthy.iterrows():
                dep_pct = r.get(dep_col, 0)
                p = str(r.get(prod_col, "ITEM"))
                if dep_pct <= 30:
                    tips.append(f"Manter '{p}' fora de promo. Venda orgânica consistente ({100-dep_pct:.1f}% sem cupom).")
        except Exception:
            pass

    # 3) Itens com margem bruta ruim (ficha técnica)
    if cost_df is not None and len(cost_df):
        try:
            bad_margin = cost_df.sort_values("margem_bruta_%").head(10)
            for _, r in bad_margin.iterrows():
                p = str(r.get("produto", "ITEM"))
                mb = r.get("margem_bruta_%", 0) * 100
                tips.append(f"Rever custo/preço de '{p}' (margem bruta {mb:.1f}%).")
        except Exception:
            pass

    # 4) Alertas diretos
    if cost_df is not None and len(cost_df):
        try:
            # risco: preço muito próximo do custo de receita
            tight = cost_df[cost_df["margem_bruta_%"] < 0.15]
            for _, r in tight.iterrows():
                p = str(r.get("produto", "ITEM"))
                tips.append(f"Atenção: '{p}' com margem < 15%. Ajustar preço, porcionamento ou negociar insumos.")
        except Exception:
            pass

    # Remover duplicadas mantendo ordem
    seen = set()
    final = []
    for t in tips:
        if t not in seen:
            seen.add(t)
            final.append(t)
    return final

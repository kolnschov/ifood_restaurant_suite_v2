import json, io, os
import pandas as pd
import numpy as np
import streamlit as st

# módulos locais
from modules.data_io import load_config, save_config
from modules.analytics import (
    kpis_pedidos,
    incentivos_por_origem,
    dependencia_por_produto,
    margem_pos_taxa,
)
from modules.costing import compute_costs, summarize_pricing
from modules.assistant import advice

st.set_page_config(page_title="Suite iFood Restaurantes — v2", layout="wide")
st.title("Suite iFood Restaurantes — v2")

# ---------------- Configuração (sidebar) ----------------
with st.sidebar:
    st.subheader("Configuração")
    cfg = load_config()

    # Modo de entrega com taxa automática
    delivery = st.radio(
        "Tipo de entrega",
        ["Entrega própria", "Entrega pelo iFood (Logística)"],
        index=0 if cfg.get("delivery_mode") == "Entrega própria" else 1,
    )
    taxa_ifood_pct = 0.20 if delivery == "Entrega própria" else 0.36
    st.write(f"**Taxa aplicada automaticamente:** {int(taxa_ifood_pct*100)}%")

    custo_moto = st.number_input(
        "Custo médio por entrega própria (R$)",
        min_value=0.0, max_value=50.0,
        value=float(cfg.get("custo_entrega_propria", 8.0)),
        step=0.5, format="%.2f"
    )

    if st.button("Salvar configuração"):
        new_cfg = {
            "delivery_mode": delivery,
            "taxa_ifood_pct": float(taxa_ifood_pct),   # 0.20 ou 0.36
            "custo_entrega_propria": float(custo_moto),
        }
        save_config(new_cfg)
        st.success("Configuração salva.")

st.caption("A taxa é definida automaticamente: 20% (Entrega própria) ou 36% (Logística iFood).")

# ---------------- Guia de dados ----------------
with st.expander("Onde baixar cada relatório (clique para abrir)"):
    guide = json.load(open("assets/data_guide.json", "r", encoding="utf-8"))
    for _, info in guide.items():
        st.subheader(info["nome_relatorio"])
        st.write(" -> ".join(info.get("onde_encontrar", [])))
        if "abas_interessantes" in info:
            st.caption("Abas: " + ", ".join(info["abas_interessantes"]))
        if "observacao" in info:
            st.caption(info["observacao"])

# =====================================================================
# 1) UPLOADS — OBRIGATÓRIO ANTES DA FICHA TÉCNICA
# =====================================================================
st.header("Uploads de relatórios (obrigatório antes da ficha técnica)")
col1, col2 = st.columns(2)
with col1:
    up_ped = st.file_uploader("Relatório de Pedidos (.xlsx)", type=["xlsx"], key="ped")
    up_card = st.file_uploader("Relatório de Cardápio/Funil (.xlsx) — use a aba Itens", type=["xlsx"], key="card")
with col2:
    up_vendas = st.file_uploader("Relatório de Vendas (.xlsx)", type=["xlsx"], key="vend")
    up_oper = st.file_uploader("Relatório de Operação (.xlsx)", type=["xlsx"], key="oper")

# Detecta produtos a partir dos uploads
produtos_detectados = []
df_itens = None
df_ped = None
try:
    if up_card:
        df_itens = pd.read_excel(up_card, sheet_name="Itens")
        col_nome = None
        for c in df_itens.columns:
            if str(c).strip().lower() in ["produto", "nome do item", "item", "nome"]:
                col_nome = c
                break
        if col_nome:
            produtos_detectados = sorted(list({str(x).strip() for x in df_itens[col_nome].dropna().tolist()}))
except Exception as e:
    st.warning(f"Não consegui ler a aba 'Itens' do Cardápio/Funil: {e}")

# fallback com Pedidos ou Vendas
if not produtos_detectados:
    try:
        if up_ped:
            df_ped = pd.read_excel(up_ped)
            cand = [c for c in df_ped.columns if "produto" in c.lower() or "item" in c.lower()]
            if cand:
                c = cand[0]
                produtos_detectados = sorted(list({str(x).strip() for x in df_ped[c].dropna().tolist()}))
    except Exception:
        pass

if not produtos_detectados and up_vendas:
    try:
        df_vend = pd.read_excel(up_vendas)
        cand = [c for c in df_vend.columns if "produto" in c.lower() or "item" in c.lower()]
        if cand:
            c = cand[0]
            produtos_detectados = sorted(list({str(x).strip() for x in df_vend[c].dropna().tolist()}))
    except Exception:
        pass

# Mantém no estado
if "produtos_detectados" not in st.session_state:
    st.session_state.produtos_detectados = []
if produtos_detectados:
    st.session_state.produtos_detectados = produtos_detectados

# =====================================================================
# 2) TABELA DE PREÇOS/VOLUMES E PARÂMETROS POR PRODUTO
# =====================================================================
st.subheader("Produtos detectados nos relatórios")
if len(st.session_state.produtos_detectados) == 0:
    st.info("Envie **Cardápio/Funil (Itens)** para detectar a lista de produtos. Sem isso, a ficha técnica fica bloqueada.")
else:
    # inicializa tabela “preços/volume/margem/desc”
    if "tabela_precos" not in st.session_state:
        st.session_state.tabela_precos = pd.DataFrame({
            "produto": st.session_state.produtos_detectados,
            "preco_ifood": [0.0]*len(st.session_state.produtos_detectados),
            "volume_mensal": [0]*len(st.session_state.produtos_detectados),
            "margem_alvo_%": [30.0]*len(st.session_state.produtos_detectados),
            "desconto_medio_R$": [0.0]*len(st.session_state.produtos_detectados)
        })
    else:
        existentes = set(st.session_state.tabela_precos["produto"].tolist())
        novos = [p for p in st.session_state.produtos_detectados if p not in existentes]
        if novos:
            st.session_state.tabela_precos = pd.concat([
                st.session_state.tabela_precos,
                pd.DataFrame({
                    "produto": novos,
                    "preco_ifood": [0.0]*len(novos),
                    "volume_mensal": [0]*len(novos),
                    "margem_alvo_%": [30.0]*len(novos),
                    "desconto_medio_R$": [0.0]*len(novos)
                })
            ], ignore_index=True)

    st.caption("Preencha preço iFood, volume mensal, margem alvo (%) e o desconto médio em R$ (efeito de cupons).")
    st.session_state.tabela_precos = st.data_editor(
        st.session_state.tabela_precos,
        column_config={
            "produto": st.column_config.TextColumn("produto", disabled=True),
            "preco_ifood": st.column_config.NumberColumn("preco_ifood", step=0.5, format="%.2f"),
            "volume_mensal": st.column_config.NumberColumn("volume_mensal", step=10),
            "margem_alvo_%": st.column_config.NumberColumn("margem_alvo_%", help="Alvo de margem líquida, em %"),
            "desconto_medio_R$": st.column_config.NumberColumn("desconto_medio_R$", step=0.5, format="%.2f", help="Desconto médio por pedido (cupons/benefícios)")
        },
        use_container_width=True
    )

# =====================================================================
# 3) FICHA TÉCNICA (CADASTRO GUIADO) E PRECIFICAÇÃO POR PRODUTO
# =====================================================================
st.header("Ficha técnica e precificação por produto")

if len(st.session_state.get("produtos_detectados", [])) == 0:
    st.warning("⚠️ Primeiro envie as planilhas e confirme os **Produtos detectados** acima.")
else:
    # estado
    if "insumos_df" not in st.session_state:
        st.session_state.insumos_df = pd.DataFrame(columns=["insumo","unidade","custo_unitario"])
    if "comp_df" not in st.session_state:
        st.session_state.comp_df = pd.DataFrame(columns=["produto","preco_venda_atual","insumo","quantidade","unidade","custo_unitario"])

    # sub-abas
    t1, t2, t3, t4, t5 = st.tabs([
        "Custos fixos","Insumos","Composição por produto","Precificação por produto","Resumo & salvar"
    ])

    # ---- Custos fixos
    with t1:
        if "fixos" not in st.session_state:
            st.session_state.fixos = {
                "aluguel": 0.0, "energia": 0.0, "agua": 0.0, "gas": 0.0,
                "folha": 0.0, "marketing": 0.0, "outros": 0.0
            }
        fixos = st.session_state.fixos
        c1,c2,c3 = st.columns(3)
        fixos["aluguel"]   = c1.number_input("Aluguel (R$/mês)", 0.0, 1e6, fixos["aluguel"], 50.0)
        fixos["energia"]   = c2.number_input("Energia (R$/mês)", 0.0, 1e6, fixos["energia"], 50.0)
        fixos["agua"]      = c3.number_input("Água (R$/mês)",    0.0, 1e6, fixos["agua"], 50.0)
        c1,c2,c3 = st.columns(3)
        fixos["gas"]       = c1.number_input("Gás (R$/mês)",     0.0, 1e6, fixos["gas"], 50.0)
        fixos["folha"]     = c2.number_input("Folha (R$/mês)",   0.0, 1e6, fixos["folha"], 50.0)
        fixos["marketing"] = c3.number_input("Marketing (R$/mês)",0.0, 1e6, fixos["marketing"], 50.0)
        fixos["outros"]    = st.number_input("Outros fixos (R$/mês)", 0.0, 1e6, fixos["outros"], 50.0)
        st.success("Custos fixos salvos na sessão.")

    # ---- Insumos
    with t2:
        st.write("Cadastre insumos com unidade e custo unitário.")
        with st.form("add_insumo_form", clear_on_submit=True):
            ins = st.text_input("Nome do insumo")
            und = st.text_input("Unidade (ex: un, g, ml, fatia)")
            cus = st.number_input("Custo unitário (R$ por unidade acima)", 0.0, 1e6, 0.0, 0.01)
            ok = st.form_submit_button("Adicionar insumo")
            if ok and ins:
                st.session_state.insumos_df = pd.concat([
                    st.session_state.insumos_df,
                    pd.DataFrame([{"insumo":ins,"unidade":und,"custo_unitario":cus}])
                ], ignore_index=True)
        st.dataframe(st.session_state.insumos_df, use_container_width=True)

    # ---- Composição por produto
    with t3:
        st.write("Selecione um produto detectado e adicione seus insumos e quantidades. O preço iFood vem da tabela acima.")
        ins_list = st.session_state.insumos_df["insumo"].tolist()
        produtos = st.session_state.produtos_detectados

        with st.form("add_comp_form", clear_on_submit=True):
            prod = st.selectbox("Produto", options=["(selecione)"] + produtos)
            insumo = st.selectbox("Insumo", options=["(selecione)"] + ins_list)
            qtd    = st.number_input("Quantidade do insumo", 0.0, 1e6, 0.0, 1.0)
            und    = st.text_input("Unidade do insumo (ex: g, un)")
            add    = st.form_submit_button("Adicionar à composição")
            if add and prod != "(selecione)" and insumo != "(selecione)":
                # custo unitário do insumo
                try:
                    c_uni = float(st.session_state.insumos_df.loc[
                        st.session_state.insumos_df["insumo"]==insumo, "custo_unitario"
                    ].iloc[0])
                except Exception:
                    c_uni = 0.0
                # preço iFood cadastrado
                try:
                    preco_ifood = float(st.session_state.tabela_precos.loc[
                        st.session_state.tabela_precos["produto"]==prod, "preco_ifood"
                    ].iloc[0])
                except Exception:
                    preco_ifood = 0.0

                st.session_state.comp_df = pd.concat([
                    st.session_state.comp_df,
                    pd.DataFrame([{
                        "produto":prod,
                        "preco_venda_atual":preco_ifood,
                        "insumo":insumo,
                        "quantidade":qtd,
                        "unidade":und,
                        "custo_unitario":c_uni
                    }])
                ], ignore_index=True)

        if len(st.session_state.comp_df):
            st.dataframe(st.session_state.comp_df, use_container_width=True)
        else:
            st.info("Nenhum item de ficha técnica cadastrado ainda. Adicione insumos ao produto.")

    # ---- Precificação por produto (comparar margem alvo vs. preço iFood, com desconto)
    with t4:
        if len(st.session_state.produtos_detectados) == 0:
            st.info("Sem produtos para precificar.")
        else:
            prod_sel = st.selectbox("Escolha um produto para analisar", options=st.session_state.produtos_detectados)
            # puxa dados
            preco_ifood = float(st.session_state.tabela_precos.loc[
                st.session_state.tabela_precos["produto"]==prod_sel, "preco_ifood"
            ].iloc[0]) if prod_sel in st.session_state.tabela_precos["produto"].values else 0.0

            margem_alvo_local = float(st.session_state.tabela_precos.loc[
                st.session_state.tabela_precos["produto"]==prod_sel, "margem_alvo_%"
            ].iloc[0]) / 100.0 if prod_sel in st.session_state.tabela_precos["produto"].values else 0.30

            desc_medio = float(st.session_state.tabela_precos.loc[
                st.session_state.tabela_precos["produto"]==prod_sel, "desconto_medio_R$"
            ].iloc[0]) if prod_sel in st.session_state.tabela_precos["produto"].values else 0.0

            # custo receita do produto
            comp = st.session_state.comp_df[st.session_state.comp_df["produto"]==prod_sel].copy()
            if len(comp)==0:
                st.warning("Cadastre a composição do produto na aba anterior.")
            else:
                comp["custo_total_insumo"] = pd.to_numeric(comp["quantidade"], errors="coerce").fillna(0) * \
                                             pd.to_numeric(comp["custo_unitario"], errors="coerce").fillna(0)
                custo_receita = comp["custo_total_insumo"].sum()

                # receita líquida sem e com cupom (aprox)
                if delivery == "Entrega pelo iFood (Logística)":
                    rec_liq_sem = preco_ifood * (1 - float(taxa_ifood_pct))
                    rec_liq_com = max(0.0, preco_ifood - desc_medio) * (1 - float(taxa_ifood_pct))
                else:
                    rec_liq_sem = preco_ifood - float(custo_moto)
                    rec_liq_com = max(0.0, preco_ifood - desc_medio) - float(custo_moto)

                # mostramos compare
                c1, c2, c3 = st.columns(3)
                c1.metric("Preço iFood", f"R$ {preco_ifood:,.2f}".replace(",", "X").replace(".", ",").replace("X","."))

                c2.metric("Receita líquida s/ cupom", f"R$ {rec_liq_sem:,.2f}".replace(",", "X").replace(".", ",").replace("X","."))
                c3.metric("Receita líquida c/ cupom", f"R$ {rec_liq_com:,.2f}".replace(",", "X").replace(".", ",").replace("X","."))

                st.caption(f"Custo de receita (insumos) atual: R$ {custo_receita:,.2f}".replace(",", "X").replace(".", ",").replace("X","."))

                # margem líquida vs alvo (sem considerar fixos aqui para resposta rápida; o resumo completo considera fixos)
                margem_liq_sem = rec_liq_sem - custo_receita
                margem_liq_com = rec_liq_com - custo_receita

                st.write(f"**Margem líquida aprox. sem cupom:** R$ {margem_liq_sem:,.2f}".replace(",", "X").replace(".", ",").replace("X","."))
                st.write(f"**Margem líquida aprox. com cupom:** R$ {margem_liq_com:,.2f}".replace(",", "X").replace(".", ",").replace("X","."))

                # preço sugerido para atingir a margem alvo (sem cupom) usando fórmula do summarize_pricing
                # var = custo_receita + embalagem (aqui supomos embalagem zero, pois vem do resumo completo)
                st.info("O **Resumo & salvar** abaixo calcula com fixos, embalagem, impostos e sugere preço ideal para bater a margem alvo.")

    # ---- Resumo & salvar (com descontos médios)
    with t5:
        ficha_df = st.session_state.comp_df.copy()
        ficha_df = ficha_df[["produto","preco_venda_atual","insumo","quantidade","unidade","custo_unitario"]]
        if len(ficha_df)==0 or "tabela_precos" not in st.session_state or st.session_state.tabela_precos["preco_ifood"].fillna(0).sum()==0:
            st.warning("⚠️ Preencha a **tabela de preços/volumes** e **a composição dos produtos** para ver o resumo.")
        else:
            volume_por_produto = {r["produto"]: int(r["volume_mensal"] or 0)
                                  for _, r in st.session_state.tabela_precos.iterrows()}
            # mapeia descontos médios e substitui preco_venda_atual pelos preços de tabela
            desconto_map = {r["produto"]: float(r["desconto_medio_R$"] or 0.0)
                            for _, r in st.session_state.tabela_precos.iterrows()}
            # garantir que o "preco_venda_atual" do comp_df reflita a tabela
            for p, pv in zip(st.session_state.tabela_precos["produto"], st.session_state.tabela_precos["preco_ifood"]):
                ficha_df.loc[ficha_df["produto"]==p, "preco_venda_atual"] = float(pv or 0.0)

            # margem alvo global como fallback, mas o summarize usa por produto via preço sugerido sem cupom
            pricing = summarize_pricing(
                ficha_df=ficha_df,
                custos_fixos=st.session_state.fixos,
                volume_por_produto=volume_por_produto,
                impostos_pct=0.0,                  # impostos % se quiser considerar agora, troque aqui
                custo_embalagem=0.0,               # custo embalagem unitário médio (global) se aplicável
                delivery_mode=delivery,
                taxa_ifood_pct=float(taxa_ifood_pct),
                custo_entrega=float(custo_moto),
                margem_alvo_pct=0.30,              # alvo global padrão; você já ajusta por produto na tabela acima para consulta
                desconto_medio_por_produto=desconto_map
            )
            st.subheader("Resumo por produto (margem com e sem cupom)")
            st.dataframe(pricing, use_container_width=True)

            # salvar ficha técnica compatível com o restante do app
            save_like_editor = ficha_df.rename(columns={"preco_venda_atual":"preco_venda"})
            os.makedirs("storage", exist_ok=True)
            save_like_editor.to_csv("storage/ficha_tecnica.csv", index=False)
            st.success("Ficha técnica salva em storage/ficha_tecnica.csv")
            st.download_button(
                "Baixar ficha técnica (CSV)",
                data=save_like_editor.to_csv(index=False).encode("utf-8"),
                file_name="ficha_tecnica.csv"
            )

# =====================================================================
# 4) ANÁLISES (mantidas)
# =====================================================================
st.header("Análises")
tabs = st.tabs(["KPIs & Incentivos", "Produtos", "Margem real (com ficha)", "Recomendações", "IA"])

# KPIs & incentivos
with tabs[0]:
    if up_ped is not None:
        if df_ped is None:
            try:
                df_ped = pd.read_excel(up_ped)
            except Exception as e:
                st.error(f"Erro lendo Pedidos: {e}")
                df_ped = None
    if df_ped is not None:
        st.subheader("KPIs de pedidos")
        st.dataframe(kpis_pedidos(df_ped))
        st.subheader("Incentivos por origem")
        st.dataframe(incentivos_por_origem(df_ped))
    else:
        st.info("Envie Pedidos para ver KPIs.")

# Produtos (dependência de promoção)
prod_full = None
with tabs[1]:
    if df_itens is not None:
        try:
            prod_full, top_dep, top_ind, equil = dependencia_por_produto(df_itens)
            st.subheader("Visão completa por produto (dependência de promo)")
            st.dataframe(prod_full)
            c1, c2, c3 = st.columns(3)
            with c1:
                st.write("Top dependentes")
                st.dataframe(top_dep)
            with c2:
                st.write("Top independentes")
                st.dataframe(top_ind)
            with c3:
                st.write("Equilibrados")
                st.dataframe(equil)
        except Exception as e:
            st.error(f"Erro processando Cardápio/Funil: {e}")
    else:
        st.info("Envie Cardápio/Funil (Itens).")

# Margem real combinando ficha + configuração
with tabs[2]:
    if len(st.session_state.get("comp_df", [])) == 0:
        st.info("Use a aba Ficha técnica para montar seus produtos.")
    else:
        cost_table = compute_costs(
            st.session_state.comp_df.rename(columns={"preco_venda_atual":"preco_venda"})
        )
        st.subheader("Custos e margem bruta (antes de taxas/cuponagem)")
        st.dataframe(cost_table)

        st.subheader("Estimativa de margem líquida por produto (após taxa/entrega)")
        mode = delivery
        taxa = float(taxa_ifood_pct)     # 0.20 ou 0.36
        custo_ent = float(custo_moto)
        m = cost_table.copy()
        m["margem_liquida_R$_aprox"] = m.apply(
            lambda r: margem_pos_taxa(r["preco_venda"], r["custo_receita"], mode, taxa, custo_ent),
            axis=1,
        )
        m["margem_liquida_%_aprox"] = np.where(
            m["preco_venda"] > 0, m["margem_liquida_R$_aprox"] / m["preco_venda"], 0.0
        )
        st.dataframe(m)

# Recomendações
with tabs[3]:
    tips = advice(
        prod_full,
        compute_costs(st.session_state.comp_df.rename(columns={"preco_venda_atual":"preco_venda"}))
        if len(st.session_state.get("comp_df", [])) else None
    )
    if tips:
        for t in tips:
            st.write("• " + t)
    else:
        st.info("Preencha ficha técnica e/ou envie Cardápio para ver recomendações.")

# IA simples
with tabs[4]:
    q = st.text_input("Pergunte sobre promoções, margens, preços...")
    if st.button("Responder", key="ask"):
        respostas = []
        if prod_full is not None and "depend" in q.lower():
            dep = prod_full.sort_values("%_com_promo", ascending=False).head(5)
            respostas.append(
                "Mais dependentes de promoção: " + ", ".join(dep["Produto"].astype(str).tolist())
            )
        if len(st.session_state.get("comp_df", [])):
            cost_tab = compute_costs(
                st.session_state.comp_df.rename(columns={"preco_venda_atual":"preco_venda"})
            )
            if "margem" in q.lower():
                low = cost_tab.sort_values("margem_bruta_%").head(5)
                respostas.append(
                    "Piores margens (bruta): " + ", ".join(low["produto"].astype(str).tolist())
                )
            if "preço" in q.lower() or "preco" in q.lower():
                mode = delivery
                taxa = float(taxa_ifood_pct)
                custo_ent = float(custo_moto)
                low_net = cost_tab.copy()
                low_net["margem_liq"] = low_net.apply(
                    lambda r: r["preco_venda"] * (1 - taxa) - r["custo_receita"]
                    if mode != "Entrega própria"
                    else r["preco_venda"] - custo_ent - r["custo_receita"],
                    axis=1,
                )
                bad = low_net.sort_values("margem_liq").head(5)
                respostas.append(
                    "Itens com menor margem líquida aprox.: "
                    + ", ".join(bad["produto"].astype(str).tolist())
                )
        if not respostas:
            respostas.append(
                "Forneça os relatórios, preencha preços/volumes e monte a Ficha técnica; depois pergunte com 'margem' ou 'dependência'."
            )
        st.write("\n\n".join(respostas))

st.caption("Fluxo: Upload → Produtos detectados (preço, volume, desconto, margem alvo) → Ficha técnica → Precificação por produto → Resumo.")

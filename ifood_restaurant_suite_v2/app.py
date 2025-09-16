# ===== IMPORTS =====
import os
import json
import pandas as pd
import streamlit as st
from pathlib import Path

# ===== GARANTE QUE OS CAMINHOS RELATIVOS FUNCIONEM NO DEPLOY =====
BASE_DIR = Path(__file__).resolve().parent
os.chdir(BASE_DIR)

# ===== IMPORTA OS MÓDULOS DO APP =====
from modules import data_io, analytics, costing, assistant

# ===== CONFIGURAÇÕES DA PÁGINA =====
st.set_page_config(
    page_title="Suite iFood Restaurantes — v2",
    layout="wide"
)

st.title("Suite iFood Restaurantes — v2")
st.caption("A taxa é definida automaticamente: 20% (Entrega própria) ou 36% (Logística iFood).")

# ===== INICIALIZA ESTADO =====
if "config" not in st.session_state:
    st.session_state["config"] = {
        "tipo_entrega": "propria",
        "taxa_ifood": 0.20,
        "custo_entrega": 0.0
    }

if "custos_fixos" not in st.session_state:
    st.session_state["custos_fixos"] = {
        "aluguel": 0.0,
        "energia": 0.0,
        "agua": 0.0,
        "gas": 0.0,
        "folha": 0.0,
        "marketing": 0.0,
        "outros": 0.0,
    }

if "insumos" not in st.session_state:
    st.session_state["insumos"] = {}

if "fichas" not in st.session_state:
    st.session_state["fichas"] = {}

# ===== BARRA LATERAL - CONFIGURAÇÃO =====
st.sidebar.header("Configuração")

tipo_entrega = st.sidebar.radio(
    "Tipo de entrega",
    ["Entrega própria", "Entrega pelo iFood (Logística)"]
)

if tipo_entrega == "Entrega própria":
    st.session_state["config"]["tipo_entrega"] = "propria"
    st.session_state["config"]["taxa_ifood"] = 0.20
else:
    st.session_state["config"]["tipo_entrega"] = "ifood"
    st.session_state["config"]["taxa_ifood"] = 0.36

st.markdown(
    f"**Taxa aplicada automaticamente:** {int(st.session_state['config']['taxa_ifood']*100)}%"
)

custo_entrega = st.sidebar.number_input(
    "Custo médio por entrega própria (R$)",
    min_value=0.0, step=0.5, value=st.session_state["config"]["custo_entrega"]
)
st.session_state["config"]["custo_entrega"] = custo_entrega

if st.sidebar.button("Salvar configuração"):
    st.success("Configuração salva.")

# ===== FICHA TÉCNICA E PRECIFICAÇÃO =====
st.header("Ficha técnica e precificação por produto")

aba = st.tabs([
    "Custos fixos",
    "Insumos",
    "Composição por produto",
    "Precificação por produto",
    "Resumo & salvar"
])

# --- Custos fixos
with aba[0]:
    st.subheader("Custos fixos mensais")
    for k, v in st.session_state["custos_fixos"].items():
        st.session_state["custos_fixos"][k] = st.number_input(
            f"{k.capitalize()} (R$/mês)", min_value=0.0, step=100.0, value=v
        )
    st.info("Custos fixos salvos na sessão.")

# --- Insumos
with aba[1]:
    st.subheader("Cadastro de insumos")
    nome = st.text_input("Nome do insumo")
    custo = st.number_input("Custo por unidade (R$)", min_value=0.0, step=0.01)
    unidade = st.text_input("Unidade (ex: g, ml, un)")
    if st.button("Adicionar insumo"):
        if nome:
            st.session_state["insumos"][nome] = {"custo": custo, "unidade": unidade}
            st.success(f"Insumo {nome} adicionado.")

    if st.session_state["insumos"]:
        st.write("### Insumos cadastrados")
        st.table(pd.DataFrame(st.session_state["insumos"]).T)

# --- Composição por produto
with aba[2]:
    st.subheader("Monte a ficha técnica de cada produto")
    produto = st.text_input("Nome do produto")
    if produto:
        insumo = st.selectbox("Escolha o insumo", [""] + list(st.session_state["insumos"].keys()))
        qtd = st.number_input("Quantidade do insumo", min_value=0.0, step=0.1)
        if st.button("Adicionar à composição"):
            if produto not in st.session_state["fichas"]:
                st.session_state["fichas"][produto] = []
            if insumo:
                st.session_state["fichas"][produto].append((insumo, qtd))
                st.success(f"{qtd} {st.session_state['insumos'][insumo]['unidade']} de {insumo} adicionado ao {produto}.")

    if st.session_state["fichas"]:
        st.write("### Produtos e composições")
        for prod, itens in st.session_state["fichas"].items():
            st.write(f"**{prod}**")
            for i in itens:
                st.write(f"- {i[1]} {st.session_state['insumos'][i[0]]['unidade']} de {i[0]}")

# --- Precificação por produto
with aba[3]:
    st.subheader("Precificação")
    produto = st.selectbox("Selecione o produto", [""] + list(st.session_state["fichas"].keys()))
    preco_venda = st.number_input("Preço de venda no iFood (R$)", min_value=0.0, step=0.5)

    if produto:
        custo = 0.0
        for insumo, qtd in st.session_state["fichas"][produto]:
            custo += qtd * st.session_state["insumos"][insumo]["custo"]

        taxa_ifood = preco_venda * st.session_state["config"]["taxa_ifood"]
        margem = preco_venda - (custo + taxa_ifood)

        st.metric("Custo total do produto", f"R$ {custo:.2f}")
        st.metric("Taxa iFood", f"R$ {taxa_ifood:.2f}")
        st.metric("Lucro líquido", f"R$ {margem:.2f}")

# --- Resumo
with aba[4]:
    st.subheader("Resumo da operação")
    st.write("Custos fixos", st.session_state["custos_fixos"])
    st.write("Insumos", st.session_state["insumos"])
    st.write("Fichas técnicas", st.session_state["fichas"])
    st.success("Resumo gerado. Aqui depois podemos exportar para Excel/CSV.")

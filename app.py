"""
Dashboard do projeto auditoria-obras-anomalias.

Interface de auditoria em tres telas:
  1. Visao geral       - panorama da carteira de obras
  2. Ranking de risco  - a lista priorizada (o "produto")
  3. Auditoria individual - o dossie de uma obra especifica

Rodar da RAIZ do projeto com: streamlit run app.py
"""

import os
import pandas as pd
import plotly.express as px
import streamlit as st

from src.explicar import calcular_shap, explicar_obra


# ----------------------------------------------------------------------
# Carregamento dos dados
# ----------------------------------------------------------------------

# @st.cache_data guarda o resultado na memoria: sem isso, o Streamlit
# releria o CSV e recalcularia o SHAP a cada clique na tela.
@st.cache_data
def carregar_dados():
    caminho = "data/processed/obras_risk_score.csv"
    if not os.path.exists(caminho):
        return None, None
    df = pd.read_csv(caminho)
    shap_df = calcular_shap(df)
    return df, shap_df


CORES_FAIXA = {
    "baixo": "#2E7D32",
    "medio": "#F9A825",
    "alto": "#EF6C00",
    "critico": "#C62828",
}


# ----------------------------------------------------------------------
# Telas
# ----------------------------------------------------------------------

def tela_visao_geral(df):
    st.header("Visao geral da carteira")

    # st.columns cria colunas lado a lado. st.metric mostra um numero
    # grande com rotulo, ideal para indicadores de topo.
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Obras", len(df))
    col2.metric("Valor contratado", f"R$ {df['valor_contratado'].sum()/1e6:,.0f}mi")
    col3.metric("Risco alto/critico", int((df["faixa_risco"].isin(["alto", "critico"])).sum()))
    col4.metric("Risk score medio", f"{df['risk_score'].mean():.0f}")

    st.subheader("Distribuicao por faixa de risco")
    contagem = df["faixa_risco"].value_counts().reindex(["baixo", "medio", "alto", "critico"])
    fig = px.bar(
        x=contagem.index,
        y=contagem.values,
        color=contagem.index,
        color_discrete_map=CORES_FAIXA,
        labels={"x": "faixa", "y": "obras"},
    )
    fig.update_layout(showlegend=False)
    st.plotly_chart(fig, use_container_width=True)

    st.subheader("Risk score por tipo de empreendimento")
    fig2 = px.box(df, x="tipo_empreendimento", y="risk_score", points="outliers")
    st.plotly_chart(fig2, use_container_width=True)


def tela_ranking(df):
    st.header("Ranking de risco")
    st.caption("Obras ordenadas pela prioridade de investigacao.")

    # Filtros na barra lateral
    faixas = st.sidebar.multiselect(
        "Faixas de risco",
        options=["baixo", "medio", "alto", "critico"],
        default=["alto", "critico"],
    )
    tipos = st.sidebar.multiselect(
        "Tipo de empreendimento",
        options=sorted(df["tipo_empreendimento"].unique()),
        default=sorted(df["tipo_empreendimento"].unique()),
    )

    filtrado = df[
        df["faixa_risco"].isin(faixas) & df["tipo_empreendimento"].isin(tipos)
    ].sort_values("risk_score", ascending=False)

    st.write(f"{len(filtrado)} obras encontradas")

    colunas = [
        "id_obra", "tipo_empreendimento", "cidade", "uf",
        "valor_contratado", "risk_score", "faixa_risco",
    ]
    st.dataframe(filtrado[colunas], use_container_width=True, hide_index=True)


def tela_auditoria(df, shap_df):
    st.header("Auditoria individual")

    # As obras de maior risco aparecem primeiro na selecao.
    ids_ordenados = df.sort_values("risk_score", ascending=False)["id_obra"].tolist()
    id_obra = st.selectbox("Selecione a obra", options=ids_ordenados)

    obra = df[df["id_obra"] == id_obra].iloc[0]

    col1, col2 = st.columns([1, 2])

    with col1:
        st.metric("Risk Score", f"{obra['risk_score']:.0f}")
        faixa = str(obra["faixa_risco"])
        st.markdown(
            f"<span style='color:{CORES_FAIXA[faixa]};font-weight:bold'>"
            f"FAIXA: {faixa.upper()}</span>",
            unsafe_allow_html=True,
        )
        st.write(f"**Tipo:** {obra['tipo_empreendimento']}")
        st.write(f"**Local:** {obra['cidade']}/{obra['uf']}")
        st.write(f"**Empresa:** {obra['empresa_responsavel']}")

    with col2:
        st.subheader("Justificativa")
        texto = explicar_obra(df, shap_df, id_obra)
        st.text(texto)

    # Boxplot posicionando a obra dentro do seu peer group
    st.subheader("Posicao no peer group")
    indicador = st.selectbox(
        "Indicador",
        options=["custo_por_m2", "pct_aditivos", "m2_por_funcionario", "estouro_prazo_pct"],
    )
    grupo = df[df["tipo_empreendimento"] == obra["tipo_empreendimento"]]
    fig = px.box(grupo, y=indicador, points="all")
    fig.add_hline(
        y=obra[indicador],
        line_color="red",
        annotation_text=f"esta obra: {obra[indicador]:,.1f}",
    )
    st.plotly_chart(fig, use_container_width=True)


# ----------------------------------------------------------------------
# App principal
# ----------------------------------------------------------------------

def main():
    st.set_page_config(page_title="Auditoria de Obras", layout="wide")
    st.title("Auditoria de Obras - Deteccao de Anomalias")

    df, shap_df = carregar_dados()

    if df is None:
        st.error("Arquivo data/processed/obras_risk_score.csv nao encontrado. "
                 "Rode antes: python main.py")
        return

    tela = st.sidebar.radio(
        "Navegacao",
        ["Visao geral", "Ranking de risco", "Auditoria individual"],
    )

    if tela == "Visao geral":
        tela_visao_geral(df)
    elif tela == "Ranking de risco":
        tela_ranking(df)
    else:
        tela_auditoria(df, shap_df)


if __name__ == "__main__":
    main()


import numpy as np
import pandas as pd
import shap
from sklearn.ensemble import IsolationForest

from src.detectores import INDICADORES, preparar_matriz


# Nomes amigaveis para as frases (o auditor nao quer ler "pct_aditivos").
NOMES_LEGIVEIS = {
    "custo_por_m2": "custo por m2",
    "custo_por_funcionario": "custo por funcionario",
    "custo_diario": "custo diario",
    "pct_aditivos": "percentual de aditivos",
    "pct_execucao": "percentual de execucao",
    "proporcao_materiais": "proporcao de materiais",
    "proporcao_mao_de_obra": "proporcao de mao de obra",
    "m2_por_funcionario": "produtividade (m2 por funcionario)",
    "dias_por_m2": "dias por m2",
    "estouro_prazo_pct": "estouro de prazo",
    "fornecedores_por_milhao": "fornecedores por milhao",
}

COLUNAS_FLAG = ["flag_estatistica", "flag_iforest", "flag_lof"]


def calcular_shap(df, seed=42, contaminacao=0.06):
    """
    Treina o Isolation Forest (mesma seed dos detectores) e calcula,
    para cada obra e cada indicador, a contribuicao SHAP.

    Devolve um DataFrame: uma linha por obra, uma coluna por indicador,
    com o valor da contribuicao. Positivo = empurrou para "mais anomala".
    """
    matriz = preparar_matriz(df)

    modelo = IsolationForest(
        n_estimators=300,
        contamination=contaminacao,
        random_state=seed,
    )
    modelo.fit(matriz)

    # TreeExplainer entende modelos baseados em arvores, como o iForest.
    explainer = shap.TreeExplainer(modelo)
    valores_shap = explainer.shap_values(matriz)

    # O sinal do SHAP no iForest e invertido em relacao ao nosso score
    # (no modelo, score baixo = anomalo). Invertemos para que
    # positivo signifique "contribuiu para o risco".
    return pd.DataFrame(-valores_shap, columns=INDICADORES, index=df.index)


def explicar_obra(df, shap_df, id_obra, grupo="tipo_empreendimento", top_n=3):
    """
    Monta a justificativa em texto de uma unica obra.

    top_n: quantos motivos principais listar.
    """
    mask = df["id_obra"] == id_obra
    linha = df[mask].iloc[0]
    idx = linha.name

    # --- cabecalho ---
    score = linha["risk_score"]
    faixa = str(linha["faixa_risco"]).upper()
    partes = [f"Obra {id_obra} | Risk Score {score:.0f} ({faixa})"]

    # --- motivos vindos do SHAP (as variaveis que mais pesaram) ---
    contribuicoes = shap_df.loc[idx].sort_values(ascending=False)
    principais = contribuicoes.head(top_n)

    for indicador, peso in principais.items():
        if peso <= 0:
            continue  # so lista o que empurrou o risco para cima

        nome = NOMES_LEGIVEIS[indicador]
        valor_obra = linha[indicador]

        # Compara com a mediana do peer group para dar contexto ao numero.
        mediana_grupo = df[df[grupo] == linha[grupo]][indicador].median()
        if mediana_grupo != 0:
            diferenca = (valor_obra / mediana_grupo - 1) * 100
            direcao = "acima" if diferenca > 0 else "abaixo"
            partes.append(
                f"- {nome}: {valor_obra:,.1f} "
                f"({abs(diferenca):.0f}% {direcao} da mediana do grupo)"
            )
        else:
            partes.append(f"- {nome}: {valor_obra:,.1f}")

    # --- concordancia entre detectores ---
    # Lemos direto do DataFrame (nao da Series 'linha') para preservar
    # os tipos booleanos. Somar ao longo da linha (axis=1) conta quantos
    # detectores marcaram True nesta obra.
    qtd = int(df.loc[mask, COLUNAS_FLAG].sum(axis=1).iloc[0])
    partes.append(f"- flagrada por {qtd}/3 detectores")

    return "\n".join(partes)


def main():
    df = pd.read_csv("data/processed/obras_risk_score.csv")
    shap_df = calcular_shap(df)

    # Explica as 5 obras de maior risco como demonstracao.
    top5 = df.sort_values("risk_score", ascending=False).head(5)
    for id_obra in top5["id_obra"]:
        print(explicar_obra(df, shap_df, id_obra))
        print()


if __name__ == "__main__":
    main()
"""
Detectores de anomalia do projeto auditoria-obras-anomalias.

Tres camadas, da mais interpretavel para a mais sofisticada:
1. Flags estatisticas (z-score e IQR por peer group)
2. Isolation Forest (anomalias multivariadas)
3. Local Outlier Factor (anomalias de densidade local)

Todos sao NAO supervisionados: nunca veem o gabarito.
"""

import numpy as np
import pandas as pd
from sklearn.preprocessing import StandardScaler
from sklearn.ensemble import IsolationForest
from sklearn.neighbors import LocalOutlierFactor

# Indicadores que alimentam os detectores multivariados.
INDICADORES = [
    "custo_por_m2", "custo_por_funcionario", "custo_diario",
    "pct_aditivos", "pct_execucao", "proporcao_materiais",
    "proporcao_mao_de_obra", "m2_por_funcionario", "dias_por_m2",
    "estouro_prazo_pct", "fornecedores_por_milhao",
]


# ----------------------------------------------------------------------
# Camada 1: flags estatisticas
# ----------------------------------------------------------------------

def zscore_por_grupo(df, coluna, grupo):
    """Z-score de cada obra em relacao ao seu proprio peer group."""
    media = df.groupby(grupo)[coluna].transform("mean")
    desvio = df.groupby(grupo)[coluna].transform("std")
    return (df[coluna] - media) / desvio


def flag_iqr_por_grupo(df, coluna, grupo):
    """True para obras fora da cerca de Tukey dentro do seu grupo."""
    q1 = df.groupby(grupo)[coluna].transform(lambda x: x.quantile(0.25))
    q3 = df.groupby(grupo)[coluna].transform(lambda x: x.quantile(0.75))
    iqr = q3 - q1
    return (df[coluna] > q3 + 1.5 * iqr) | (df[coluna] < q1 - 1.5 * iqr)


def contar_flags_estatisticas(df, grupo="tipo_empreendimento"):
    """
    Aplica z-score e IQR em TODOS os indicadores e conta quantas
    flags cada obra acumulou. Devolve uma Series com a contagem.

    Obra normal: 0 ou 1 flag (acaso estatistico acontece).
    Obra suspeita: varias flags, em varios indicadores.
    """
    total_flags = pd.Series(0, index=df.index)

    for indicador in INDICADORES:
        flag_z = zscore_por_grupo(df, indicador, grupo).abs() > 3
        flag_iqr = flag_iqr_por_grupo(df, indicador, grupo)
        total_flags += flag_z.astype(int) + flag_iqr.astype(int)

    return total_flags


# ----------------------------------------------------------------------
# Camada 2 e 3: detectores multivariados
# ----------------------------------------------------------------------

def preparar_matriz(df):
    """
    Seleciona os indicadores e coloca todos na mesma escala.
    Sem isso, o custo (centenas de milhares) dominaria qualquer
    calculo de distancia e os outros indicadores virariam figurantes.
    """
    scaler = StandardScaler()
    return scaler.fit_transform(df[INDICADORES])


def rodar_isolation_forest(df, contaminacao=0.06, seed=42):
    """
    Devolve um score de 0 a 1 por obra (quanto maior, mais anomala)
    e uma flag binaria para as `contaminacao`% mais isoladas.
    """
    matriz = preparar_matriz(df)

    modelo = IsolationForest(
        n_estimators=300,            # quantidade de arvores na floresta
        contamination=contaminacao,  # fracao esperada de anomalias
        random_state=seed,           # reprodutibilidade
    )
    predicao = modelo.fit_predict(matriz)   # -1 = anomalia, 1 = normal

    # score_samples: quanto MENOR, mais anomala. Invertemos e
    # normalizamos para 0-1 para ficar intuitivo (maior = pior).
    score_bruto = -modelo.score_samples(matriz)
    score = (score_bruto - score_bruto.min()) / (score_bruto.max() - score_bruto.min())

    return pd.Series(score, index=df.index), pd.Series(predicao == -1, index=df.index)


def rodar_lof(df, contaminacao=0.06, vizinhos=50):
    """
    Local Outlier Factor: compara a densidade ao redor de cada obra
    com a densidade ao redor dos vizinhos dela.

    Por que vizinhos=50 e nao o padrao 20: anomalias do mesmo tipo
    formam grupinhos de ~30 obras parecidas entre si. Com poucos
    vizinhos, o LOF olha a anomalia, ve outras anomalias iguais ao
    redor e conclui que a vizinhanca e "normal" (efeito masking).
    A regra: vizinhos deve ser MAIOR que o tamanho esperado dos
    grupos de anomalias, para forcar obras normais na comparacao.
    """
    matriz = preparar_matriz(df)

    modelo = LocalOutlierFactor(
        n_neighbors=vizinhos,
        contamination=contaminacao,
    )
    predicao = modelo.fit_predict(matriz)

    score_bruto = -modelo.negative_outlier_factor_
    score = (score_bruto - score_bruto.min()) / (score_bruto.max() - score_bruto.min())

    return pd.Series(score, index=df.index), pd.Series(predicao == -1, index=df.index)
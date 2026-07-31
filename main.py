"""
Pipeline completa do projeto auditoria-obras-anomalias.

Roda todas as etapas na ordem correta, garantindo que cada arquivo
intermediario exista antes da etapa que depende dele:

  1. gerar dados        -> data/raw/obras.csv
  2. features           -> data/processed/obras_features.csv
  3. detectores         -> data/processed/obras_scores.csv
  4. risk score         -> data/processed/obras_risk_score.csv

Rodar da RAIZ do projeto com: python main.py

Depois de rodar isto, o dashboard e o notebook 03 tem todos os
arquivos de que precisam.
"""

import os
import pandas as pd

from src.features import calcular_indicadores
from src.detectores import (
    contar_flags_estatisticas,
    rodar_isolation_forest,
    rodar_lof,
)
from src.risk_score import carregar_config, calcular_risk_score


def garantir_pastas():
    """Cria as pastas de saida se ainda nao existirem."""
    os.makedirs("data/processed", exist_ok=True)


def etapa_gerar_dados():
    """Gera o dataset bruto se ele ainda nao existir."""
    if os.path.exists("data/raw/obras.csv"):
        print("[1/4] dados brutos ja existem, pulando geracao")
        return
    print("[1/4] gerando dados brutos...")
    import src.gerar_dados as gerar_dados
    gerar_dados.main()


def etapa_features():
    print("[2/4] calculando indicadores...")
    df = pd.read_csv("data/raw/obras.csv")
    df = calcular_indicadores(df)
    df.to_csv("data/processed/obras_features.csv", index=False)


def etapa_detectores():
    print("[3/4] rodando detectores de anomalia...")
    df = pd.read_csv("data/processed/obras_features.csv")
    df["qtd_flags"] = contar_flags_estatisticas(df)
    df["flag_estatistica"] = df["qtd_flags"] >= 2
    df["score_iforest"], df["flag_iforest"] = rodar_isolation_forest(df)
    df["score_lof"], df["flag_lof"] = rodar_lof(df)
    df.to_csv("data/processed/obras_scores.csv", index=False)


def etapa_risk_score():
    print("[4/4] calculando risk score...")
    config = carregar_config()
    df = pd.read_csv("data/processed/obras_scores.csv")
    df = calcular_risk_score(df, config)
    df.to_csv("data/processed/obras_risk_score.csv", index=False)


def main():
    garantir_pastas()
    etapa_gerar_dados()
    etapa_features()
    etapa_detectores()
    etapa_risk_score()

    df = pd.read_csv("data/processed/obras_risk_score.csv")
    print("\nPipeline concluida.")
    print("\nDistribuicao por faixa de risco:")
    print(df["faixa_risco"].value_counts().sort_index().to_string())


if __name__ == "__main__":
    main()
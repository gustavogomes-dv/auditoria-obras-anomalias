
import pandas as pd
import yaml


def carregar_config(caminho="config.yaml"):
    """Le o arquivo de configuracao e devolve um dicionario."""
    with open(caminho, "r", encoding="utf-8") as arquivo:
        return yaml.safe_load(arquivo)


def normalizar_por_rank(serie):
    """
    Transforma qualquer sinal em uma nota de 0 a 100 baseada na
    POSICAO da obra na fila, nao no valor absoluto.

    rank(pct=True) devolve, para cada obra, a fracao de obras com
    valor menor ou igual ao dela (0 a 1). Multiplicamos por 100.

    Vantagem sobre min-max: um unico valor extremo nao esmaga a
    escala das demais obras.
    """
    return serie.rank(pct=True) * 100


def calcular_risk_score(df, config):
    """Adiciona as colunas risk_score e faixa_risco ao DataFrame."""
    df = df.copy()
    pesos = config["pesos"]

    # ------------------------------------------------------------
    # Passo 1: colocar todos os sinais na mesma regua (0 a 100)
    # ------------------------------------------------------------

    nota_flags = normalizar_por_rank(df["qtd_flags"])
    nota_iforest = normalizar_por_rank(df["score_iforest"])
    nota_lof = normalizar_por_rank(df["score_lof"])

    # Sinal de concentracao: POUCOS fornecedores por milhao contratado
    # e o alerta, entao invertemos o sinal antes de rankear
    # (quanto menor o indicador, maior a nota de risco).
    nota_concentracao = normalizar_por_rank(-df["fornecedores_por_milhao"])

    # ------------------------------------------------------------
    # Passo 2: combinar com os pesos do config
    # ------------------------------------------------------------

    df["risk_score"] = (
        nota_flags * pesos["flags_estatisticas"]
        + nota_iforest * pesos["isolation_forest"]
        + nota_lof * pesos["lof"]
        + nota_concentracao * pesos["concentracao_fornecedores"]
    ).round(1)

    # ------------------------------------------------------------
    # Passo 3: classificar em faixas
    # ------------------------------------------------------------

    faixas = config["faixas"]
    limites = [0, faixas["baixo"], faixas["medio"], faixas["alto"], 100]
    rotulos = ["baixo", "medio", "alto", "critico"]

    df["faixa_risco"] = pd.cut(
        df["risk_score"],
        bins=limites,
        labels=rotulos,
        include_lowest=True,
    )

    return df


def main():
    config = carregar_config()
    df = pd.read_csv("data/processed/obras_scores.csv")
    df = calcular_risk_score(df, config)

    df.to_csv("data/processed/obras_risk_score.csv", index=False)

    print("Distribuicao por faixa de risco:")
    print(df["faixa_risco"].value_counts().sort_index().to_string())

    print("\nTop 10 obras por Risk Score:")
    colunas = ["id_obra", "tipo_empreendimento", "qtd_flags", "risk_score", "faixa_risco"]
    print(df.sort_values("risk_score", ascending=False)[colunas].head(10).to_string(index=False))

    print("\nArquivo salvo: data/processed/obras_risk_score.csv")
    

if __name__ == "__main__":
    main()
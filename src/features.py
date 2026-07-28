"""
Engenharia de atributos do projeto auditoria-obras-anomalias.

Transforma as colunas cruas de obras.csv em indicadores comparaveis
entre obras de qualquer tamanho. A logica central: dividir uma coluna
pela outra neutraliza o efeito do tamanho da obra.

Uso direto:      python src/features.py
Uso como modulo: from src.features import calcular_indicadores
"""

import pandas as pd


def calcular_indicadores(df):
    """
    Recebe o DataFrame cru de obras e devolve uma copia com os
    indicadores derivados. Nao modifica o DataFrame original.
    """
    df = df.copy()

    # ------------------------------------------------------------
    # Indicadores financeiros
    # ------------------------------------------------------------

    # Quanto custou cada m2 construido. O indicador mais importante
    # da auditoria de obras: neutraliza o tamanho e permite comparar
    # uma obra de 1.500 m2 com uma de 8.000 m2.
    df["custo_por_m2"] = df["valor_executado"] / df["area_construida_m2"]

    # Custo medio por pessoa alocada.
    df["custo_por_funcionario"] = df["valor_executado"] / df["qtd_funcionarios"]

    # Velocidade de queima de dinheiro.
    df["custo_diario"] = df["valor_executado"] / df["prazo_realizado_dias"]

    # Aditivos como percentual do contrato original.
    # Referencia legal comum para obras publicas: 25%.
    df["pct_aditivos"] = df["valor_aditivos"] / df["valor_contratado"] * 100

    # Quanto do valor contratado foi de fato executado.
    # Muito acima de 100% indica estouro de orcamento.
    df["pct_execucao"] = df["valor_executado"] / df["valor_contratado"] * 100

    # Composicao do custo. Faixas normais: materiais ~55%, mao de obra ~35%.
    # Desvios grandes aqui podem indicar erro de lancamento ou desvio.
    df["proporcao_materiais"] = df["valor_materiais"] / df["valor_executado"] * 100
    df["proporcao_mao_de_obra"] = df["valor_mao_de_obra"] / df["valor_executado"] * 100

    # ------------------------------------------------------------
    # Indicadores operacionais
    # ------------------------------------------------------------

    # Produtividade: quantos m2 cada funcionario "entrega".
    # Valor BAIXO e sinal de alerta (muita gente para pouca obra).
    df["m2_por_funcionario"] = df["area_construida_m2"] / df["qtd_funcionarios"]

    # Ritmo da obra: quantos dias por m2 construido.
    df["dias_por_m2"] = df["prazo_realizado_dias"] / df["area_construida_m2"]

    # Estouro de prazo em percentual.
    # 0 = no prazo, 100 = levou o dobro do previsto.
    df["estouro_prazo_pct"] = (df["prazo_realizado_dias"] / df["prazo_previsto_dias"] - 1) * 100

    # Pulverizacao de fornecedores por milhao de reais contratado.
    # Muito baixo pode indicar concentracao em poucos fornecedores.
    df["fornecedores_por_milhao"] = df["qtd_fornecedores"] / (df["valor_contratado"] / 1e6)

    return df


def main():
    df = pd.read_csv("data/raw/obras.csv")
    df = calcular_indicadores(df)
    df.to_csv("data/processed/obras_features.csv", index=False)

    novas_colunas = [
        "custo_por_m2", "custo_por_funcionario", "custo_diario",
        "pct_aditivos", "pct_execucao", "proporcao_materiais",
        "proporcao_mao_de_obra", "m2_por_funcionario", "dias_por_m2",
        "estouro_prazo_pct", "fornecedores_por_milhao",
    ]
    print(f"{len(novas_colunas)} indicadores criados:")
    for c in novas_colunas:
        print(f"  {c}")
    print("\nArquivo salvo: data/processed/obras_features.csv")


if __name__ == "__main__":
    main()
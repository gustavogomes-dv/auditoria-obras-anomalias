"""
Gerador de dados ficticios de obras para o projeto auditoria-obras-anomalias.

O que este script faz:
1. Gera ~2000 obras "normais", com valores coerentes entre si
   (obra maior custa mais, demora mais, emprega mais gente).
2. Injeta anomalias de proposito em ~6% das obras, de 4 tipos diferentes.
3. Salva dois arquivos:
   - data/raw/obras.csv           -> SEM a coluna de anomalia (o que os detectores veem)
   - data/raw/obras_gabarito.csv  -> COM a coluna de anomalia (a resposta, para avaliacao)

Rodar com: python src/gerar_dados.py
"""

import numpy as np
import pandas as pd

# ----------------------------------------------------------------------
# Configuracao geral
# ----------------------------------------------------------------------

SEED = 42                 # garante que todo mundo gera o mesmo dataset
N_OBRAS = 2000            # total de obras
PERCENTUAL_ANOMALIAS = 0.06   # 6% das obras serao problematicas

rng = np.random.default_rng(SEED)

# Perfil de custo por tipo de empreendimento.
# custo_m2_medio: quanto custa em media o metro quadrado daquele tipo.
# custo_m2_desvio: variacao natural em torno da media.
TIPOS_EMPREENDIMENTO = {
    "residencial_popular": {"custo_m2_medio": 1800, "custo_m2_desvio": 250},
    "residencial_padrao":  {"custo_m2_medio": 3200, "custo_m2_desvio": 450},
    "comercial":           {"custo_m2_medio": 4500, "custo_m2_desvio": 700},
    "industrial":          {"custo_m2_medio": 6000, "custo_m2_desvio": 900},
}

CIDADES = [
    ("Belo Horizonte", "MG"), ("Uberlandia", "MG"), ("Contagem", "MG"),
    ("Sao Paulo", "SP"), ("Campinas", "SP"), ("Ribeirao Preto", "SP"),
    ("Rio de Janeiro", "RJ"), ("Curitiba", "PR"), ("Goiania", "GO"),
    ("Salvador", "BA"),
]

EMPRESAS = [
    "Construtora Horizonte", "Engenharia Vale Verde", "Alfa Construcoes",
    "Beta Engenharia", "Construtora Serrana", "Delta Obras",
    "Engenharia Mineira", "Construtora Planalto", "Obras & Cia",
    "Estrutural Engenharia", "Construtora Atlantica", "Vertice Engenharia",
]


# ----------------------------------------------------------------------
# Passo 1: gerar obras normais
# ----------------------------------------------------------------------

def gerar_obras_normais(n):
    """Gera n obras com valores coerentes entre si, sem anomalias."""

    obras = []

    for i in range(n):
        # --- caracteristicas basicas ---
        tipo = rng.choice(list(TIPOS_EMPREENDIMENTO.keys()))
        perfil = TIPOS_EMPREENDIMENTO[tipo]
        cidade, uf = CIDADES[rng.integers(0, len(CIDADES))]
        empresa = EMPRESAS[rng.integers(0, len(EMPRESAS))]

        # Area construida: lognormal, porque area e assimetrica a direita
        # (muitas obras medias, poucas gigantes) e nunca pode ser negativa.
        # mean=8, sigma=0.5 gera areas tipicas entre ~1500 e ~8000 m2.
        area_m2 = round(float(rng.lognormal(mean=8.0, sigma=0.5)), 0)

        # Custo por m2: normal DENTRO do tipo de empreendimento.
        # Obra industrial custa mais que popular, e isso e normal, nao anomalia.
        custo_m2 = rng.normal(perfil["custo_m2_medio"], perfil["custo_m2_desvio"])
        custo_m2 = max(custo_m2, 500)  # trava de seguranca contra valor absurdo

        # --- valores financeiros derivados ---
        valor_contratado = round(area_m2 * custo_m2, 2)

        # Aditivos normais: entre 0% e 10% do contrato
        # (aditivo e todo custo extra aprovado depois da assinatura).
        percentual_aditivo = rng.uniform(0.0, 0.10)
        valor_aditivos = round(valor_contratado * percentual_aditivo, 2)

        # Valor executado: contratado + aditivos, com pequeno ruido (+-3%).
        ruido = rng.normal(1.0, 0.03)
        valor_executado = round((valor_contratado + valor_aditivos) * ruido, 2)

        # Composicao do custo: materiais ~55%, mao de obra ~35% do executado.
        valor_materiais = round(valor_executado * rng.normal(0.55, 0.04), 2)
        valor_mao_de_obra = round(valor_executado * rng.normal(0.35, 0.03), 2)
        valor_compras = round(valor_materiais * rng.normal(1.05, 0.03), 2)

        # --- equipe e prazo ---
        # Regra simples: 1 funcionario para cada ~35 m2, com variacao.
        qtd_funcionarios = max(int(area_m2 / rng.normal(35, 5)), 3)

        # Prazo previsto cresce com a area: ~1 dia a cada 6 m2, minimo 120 dias.
        prazo_previsto = max(int(area_m2 / rng.normal(6, 0.8)), 120)

        # Prazo realizado: em media 5% acima do previsto (atraso leve e comum).
        prazo_realizado = int(prazo_previsto * rng.normal(1.05, 0.08))

        # --- operacional ---
        qtd_medicoes = max(int(prazo_realizado / 30), 1)  # ~1 medicao por mes
        qtd_fornecedores = max(int(rng.normal(15, 4)), 3)

        obras.append({
            "id_obra": 1000 + i,
            "cidade": cidade,
            "uf": uf,
            "tipo_empreendimento": tipo,
            "empresa_responsavel": empresa,
            "area_construida_m2": area_m2,
            "valor_contratado": valor_contratado,
            "valor_aditivos": valor_aditivos,
            "valor_executado": valor_executado,
            "valor_materiais": valor_materiais,
            "valor_mao_de_obra": valor_mao_de_obra,
            "valor_compras": valor_compras,
            "qtd_funcionarios": qtd_funcionarios,
            "prazo_previsto_dias": prazo_previsto,
            "prazo_realizado_dias": prazo_realizado,
            "qtd_medicoes": qtd_medicoes,
            "qtd_fornecedores": qtd_fornecedores,
            "anomalia": "nenhuma",   # por enquanto todas sao normais
        })

    return pd.DataFrame(obras)


# ----------------------------------------------------------------------
# Passo 2: injetar anomalias rotuladas
# ----------------------------------------------------------------------

def injetar_anomalias(df):
    """
    Sorteia ~6% das obras e aplica um dos 4 tipos de problema.
    A coluna 'anomalia' registra qual problema foi aplicado (o gabarito).
    """

    n_anomalias = int(len(df) * PERCENTUAL_ANOMALIAS)

    # Sorteia indices sem repeticao
    indices_sorteados = rng.choice(df.index, size=n_anomalias, replace=False)

    tipos_de_problema = [
        "custo_inflado",
        "aditivos_excessivos",
        "produtividade_baixa",
        "prazo_estourado",
    ]

    for idx in indices_sorteados:
        problema = tipos_de_problema[rng.integers(0, len(tipos_de_problema))]

        if problema == "custo_inflado":
            # Obra que custou 30% a 80% mais do que deveria.
            fator = rng.uniform(1.3, 1.8)
            df.loc[idx, "valor_executado"] = round(df.loc[idx, "valor_executado"] * fator, 2)
            df.loc[idx, "valor_materiais"] = round(df.loc[idx, "valor_materiais"] * fator, 2)
            df.loc[idx, "valor_compras"] = round(df.loc[idx, "valor_compras"] * fator, 2)

        elif problema == "aditivos_excessivos":
            # Aditivos de 30% a 60% do contrato (referencia legal comum: 25%).
            fator = rng.uniform(0.30, 0.60)
            novo_aditivo = round(df.loc[idx, "valor_contratado"] * fator, 2)
            diferenca = novo_aditivo - df.loc[idx, "valor_aditivos"]
            df.loc[idx, "valor_aditivos"] = novo_aditivo
            df.loc[idx, "valor_executado"] = round(df.loc[idx, "valor_executado"] + diferenca, 2)

        elif problema == "produtividade_baixa":
            # Mesma obra, 2x a 3x mais funcionarios: produtividade despenca
            # e o custo de mao de obra sobe junto.
            fator = rng.uniform(2.0, 3.0)
            df.loc[idx, "qtd_funcionarios"] = int(df.loc[idx, "qtd_funcionarios"] * fator)
            df.loc[idx, "valor_mao_de_obra"] = round(df.loc[idx, "valor_mao_de_obra"] * fator * 0.8, 2)
            df.loc[idx, "valor_executado"] = round(
                df.loc[idx, "valor_executado"] + df.loc[idx, "valor_mao_de_obra"] * 0.3, 2
            )

        elif problema == "prazo_estourado":
            # Obra que levou 2x a 3x o prazo previsto.
            fator = rng.uniform(2.0, 3.0)
            df.loc[idx, "prazo_realizado_dias"] = int(df.loc[idx, "prazo_previsto_dias"] * fator)
            df.loc[idx, "qtd_medicoes"] = max(int(df.loc[idx, "prazo_realizado_dias"] / 30), 1)

        df.loc[idx, "anomalia"] = problema

    return df


# ----------------------------------------------------------------------
# Passo 3: salvar os arquivos
# ----------------------------------------------------------------------

def main():
    print(f"Gerando {N_OBRAS} obras (seed={SEED})...")
    df = gerar_obras_normais(N_OBRAS)

    print("Injetando anomalias...")
    df = injetar_anomalias(df)

    resumo = df["anomalia"].value_counts()
    print("\nResumo do dataset:")
    print(resumo.to_string())

    # Gabarito: tudo, inclusive a coluna 'anomalia'
    df.to_csv("data/raw/obras_gabarito.csv", index=False)

    # Versao "cega": sem a coluna 'anomalia', e o que os detectores vao analisar
    df.drop(columns=["anomalia"]).to_csv("data/raw/obras.csv", index=False)

    print("\nArquivos salvos:")
    print("  data/raw/obras.csv           (sem gabarito)")
    print("  data/raw/obras_gabarito.csv  (com gabarito)")


if __name__ == "__main__":
    main()
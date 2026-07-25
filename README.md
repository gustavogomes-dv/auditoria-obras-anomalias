# auditoria-obras-anomalias

**Detecção de anomalias e priorização de risco em dados de obras, aplicando estatística, machine learning e explicabilidade à auditoria.**

Autor: Gustavo Gomes
Status: Planejamento
Projeto irmão: [`licita-forense`](https://github.com/gustavogomes-dv/licita-forense)

---

## 1. O que é

`auditoria-obras-anomalias` é um projeto de ciência de dados que simula o trabalho de uma equipe de auditoria analítica em uma construtora: dado um conjunto grande de obras, identificar automaticamente quais registros apresentam comportamento anômalo e merecem investigação prioritária.

O sistema não substitui o auditor. Ele responde a uma pergunta prática: **com milhares de obras e tempo limitado, quais eu olho primeiro, e por quê?**

Cada obra recebe um **Risk Score de 0 a 100**, sempre acompanhado de uma **justificativa legível** mostrando quais indicadores puxaram o score para cima. Explicabilidade aqui não é opcional: um alerta que o auditor não entende é um alerta que ele descarta.

## 2. O problema

Empresas de grande porte processam milhões de registros de obras, contratos, medições, compras e pagamentos. Auditar tudo manualmente é inviável, então a prática comum é amostragem. Na prática isso significa que a maior parte dos dados nunca é olhada, e inconsistências relevantes passam despercebidas.

A abordagem analítica inverte a lógica: em vez de amostrar aleatoriamente, usa estatística e machine learning para varrer 100% da base e concentrar a atenção humana onde a probabilidade de problema é maior.

## 3. Dados

Dataset **fictício e gerado por código** (`src/gerar_dados.py`), simulando cerca de 2.000 obras de uma construtora, com anomalias injetadas de propósito e rotuladas em uma coluna oculta. Isso permite avaliar depois se os métodos de detecção realmente as encontram.

Campos por obra:

| Grupo | Campos |
|---|---|
| Identificação | id_obra, cidade, uf, tipo_empreendimento, empresa_responsavel |
| Financeiro | valor_contratado, valor_executado, valor_aditivos, valor_materiais, valor_mao_de_obra, valor_compras |
| Físico | area_construida_m2, qtd_funcionarios, qtd_medicoes, qtd_fornecedores |
| Prazo | data_inicio, data_termino, prazo_previsto_dias, prazo_realizado_dias |

Gerar os próprios dados, em vez de baixar um CSV pronto, é uma decisão deliberada: demonstra entendimento de como as anomalias se manifestam nos dados e cria um gabarito (ground truth) para medir a taxa de acerto dos detectores.

## 4. Feature engineering

Indicadores derivados que alimentam a análise:

- **Financeiros:** custo por m², custo por funcionário, custo diário, percentual de aditivos sobre o contrato, percentual de execução (executado/contratado), proporção materiais vs. mão de obra
- **Operacionais:** m² por funcionário (produtividade), dias por m², estouro de prazo (%), fornecedores por milhão contratado
- **Estatísticos (por indicador, dentro do peer group):** z-score, distância da mediana em IQRs, percentil

Ponto central: as comparações são feitas **dentro de grupos comparáveis** (mesmo tipo de empreendimento e faixa de porte), nunca contra a média global. Uma obra industrial cara não é anômala por custar mais que uma casa popular.

## 5. Detecção de anomalias

Três camadas, da mais interpretável para a mais sofisticada:

1. **Regras estatísticas clássicas:** z-score e IQR por indicador, dentro do peer group. Baratas, explicáveis, pegam os casos óbvios.
2. **Isolation Forest:** anomalias multivariadas, obras onde nenhum indicador isolado grita, mas a combinação é improvável.
3. **Local Outlier Factor:** análise de densidade local, complementar ao Isolation Forest.

Cada método produz um sub-score independente. A concordância entre métodos é ela mesma um sinal: obra flagrada pelos três é mais suspeita que obra flagrada por um só.

## 6. Risk Score

Combinação ponderada dos sub-scores, normalizada para 0 a 100:

| Componente | Peso |
|---|---|
| Flags estatísticas (z-score / IQR) | 40% |
| Isolation Forest | 30% |
| LOF | 20% |
| Concentração de fornecedor / recorrência da empresa | 10% |

Faixas: 0 a 30 baixo · 31 a 60 médio · 61 a 80 alto · 81 a 100 crítico.

Os pesos são explícitos e configuráveis (`config.yaml`). Auditoria exige que o critério de priorização seja defensável, não uma caixa-preta.

## 7. Explicabilidade

Para cada obra no topo do ranking, o sistema gera a justificativa:

```
Obra 203 | Risk Score 91 (CRÍTICO)
- custo/m² 38% acima da mediana do peer group (P97)
- aditivos = 41% do valor contratado (limite legal de referência: 25%)
- produtividade (m²/funcionário) no P4 do grupo
- prazo realizado 2.3x o previsto
- flagrada por 3/3 detectores
```

SHAP é aplicado sobre o Isolation Forest para decompor a contribuição de cada variável nos casos multivariados.

## 8. Dashboard

Interface simples em **Streamlit** (`app.py`), com 3 telas:

1. **Visão geral:** total de obras, distribuição do Risk Score, indicadores agregados
2. **Ranking de risco:** tabela ordenada por score, com filtros por UF, tipo e faixa
3. **Auditoria individual:** seleciona uma obra e vê indicadores, posição vs. peer group (boxplots) e a justificativa completa

## 9. Estrutura do repositório

```
auditoria-obras-anomalias/
├── data/
│   ├── raw/                # dataset gerado
│   └── processed/          # features calculadas
├── notebooks/
│   ├── 01_eda.ipynb        # análise exploratória e estatística
│   ├── 02_features.ipynb   # engenharia de atributos
│   └── 03_anomalias.ipynb  # comparação dos detectores vs. gabarito
├── src/
│   ├── gerar_dados.py
│   ├── features.py
│   ├── detectores.py
│   ├── risk_score.py
│   └── explicar.py
├── tests/
├── app.py                  # dashboard Streamlit
├── config.yaml             # pesos e limiares
├── requirements.txt
└── README.md
```

## 10. Stack

Python · Pandas · NumPy · Scikit-Learn · SHAP · Plotly · Streamlit · Pytest

Sem banco de dados, sem Docker, sem API. O projeto roda com `pip install -r requirements.txt` e `streamlit run app.py`. Simplicidade de reprodução é parte do valor: quem abrir o repo consegue executar em 2 minutos.

## 11. Roadmap

**Fase 1: dados e estatística**
Gerador de dataset com anomalias rotuladas · EDA completa em notebook · flags por z-score e IQR com peer groups

**Fase 2: anomalias e Risk Score**
Isolation Forest e LOF · avaliação contra o gabarito (recall/precision dos detectores) · Risk Score combinado

**Fase 3: explicabilidade e entrega**
SHAP · geração de justificativas em texto · dashboard Streamlit · README final com prints e resultados

## 12. O que este projeto demonstra

Estatística aplicada (distribuições, outliers, análise por peer group) · detecção de anomalias avaliada contra gabarito · desenho de score interpretável · explicabilidade de modelos · visualização de dados · organização de projeto Python com testes · comunicação técnica voltada a um usuário de negócio, o auditor.
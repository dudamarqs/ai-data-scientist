# AI Data Scientist

Sistema onde o usuário envia um CSV e **conversa com seus dados** em linguagem
natural. O sistema detecta tipos, valida qualidade, faz análise exploratória,
treina modelos de Machine Learning, gera gráficos e explica tudo em português —
com um LLM atuando como orquestrador (não como calculadora).

## Princípio de arquitetura

> **O LLM orquestra; o código (pandas/sklearn) calcula.**
> O LLM decide *o que* fazer a partir da pergunta e *explica* o resultado.
> Toda matemática é determinística e auditável.

## Estrutura (cada pasta = uma camada da arquitetura)

```
app/
├── api/         # FastAPI — porta de entrada (rotas/endpoints)
├── ingestion/   # Leitura de arquivos → DataFrame
├── profiling/   # Detecção de tipos semânticos (data, moeda, ID...)
├── quality/     # Limpeza: nulos, outliers, duplicatas
├── analysis/    # EDA + estatística + ML (o coração)
├── interpret/   # SHAP / explicabilidade
├── llm/         # Orquestração (o maestro)
└── core/        # Config, logging (infra transversal)
tests/           # Pytest
data/            # CSVs (fora do Git)
notebooks/       # Exploração manual
```

## Setup

```bash
py -3.12 -m venv .venv
.venv\Scripts\activate          # Windows
pip install -r requirements.txt
```

## Status

Em construção, módulo a módulo. Ver progresso nas aulas.

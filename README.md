# 🤖 AI Data Scientist

Envie um **CSV** e **converse com seus dados em português**. O sistema detecta os
tipos semânticos das colunas, limpa os dados, faz análise exploratória, treina
modelos de Machine Learning, explica os resultados com SHAP — e responde às suas
perguntas em linguagem natural.

```
"Qual o preço típico dos produtos?"     → mediana calculada pelo pandas
"Existe relação entre preço e vendas?"  → correlação de Pearson
"O que mais influencia as vendas?"      → SHAP (valores de Shapley)
"Dá para prever a quantidade vendida?"  → treina e compara 4 modelos
```

## 🎯 O princípio de arquitetura

> ### O LLM **orquestra**. O código **calcula**.

LLMs são excelentes em linguagem e **péssimos em aritmética** — perguntar "qual a
média?" a um LLM produz um número **alucinado**. Por isso, aqui o LLM **nunca
calcula**:

```
┌──────────────────────────────────────────────────────────────┐
│  "Faça previsões de vendas para os próximos 6 meses"          │
└───────────────────────────┬──────────────────────────────────┘
                            ▼
              ┌─────────────────────────────┐
              │   LLM (o MAESTRO)           │  decide O QUE fazer
              │   → chama `treinar_modelos` │  (Tool Use)
              └──────────────┬──────────────┘
                             ▼
              ┌─────────────────────────────┐
              │  MOTOR DETERMINÍSTICO       │  faz a MATEMÁTICA
              │  pandas / sklearn / SHAP    │  (exata, auditável)
              └──────────────┬──────────────┘
                             ▼
              ┌─────────────────────────────┐
              │   LLM (o MAESTRO)           │  EXPLICA em português
              └─────────────────────────────┘
```

Todo número que sai daqui foi calculado por NumPy — nunca inventado.

## 🏗️ Arquitetura em camadas

Cada pasta é uma camada, com **uma única responsabilidade** (SRP):

```
app/
├── api/         # FastAPI — porta de entrada (upload, rotas, validação)
├── ingestion/   # Leitura confiável de arquivos → DataFrame
├── profiling/   # Detecção de tipos SEMÂNTICOS (data, moeda, CEP, ID…)
├── quality/     # Limpeza: duplicatas, moeda BR, imputação por mediana
├── analysis/    # EDA (estatística, correlação) + ML (treino e comparação)
├── interpret/   # SHAP — abre a caixa-preta do modelo
├── llm/         # Orquestração via Tool Use (o maestro)
└── core/        # Pipeline, configuração
```

**Fluxo:** `Ingestão → Profiling → Qualidade → Análise/ML → LLM`

O **profiling vem antes da limpeza** de propósito: *como* limpar depende do que a
coluna **é**. Um CEP `01310` precisa ser texto (senão perde o zero); `"R$ 3.499,90"`
precisa virar `float`; `05/01/2024` precisa virar `datetime`.

## 🚀 Como rodar

### Local

```bash
py -3.12 -m venv .venv
.venv\Scripts\activate            # Windows  (Linux/Mac: source .venv/bin/activate)
pip install -r requirements.txt

cp .env.example .env              # coloque sua GOOGLE_API_KEY (gratuita)
uvicorn app.api.main:app --reload
```

> 🔑 A chave do **Gemini é gratuita** e não pede cartão: https://aistudio.google.com/apikey
> Prefere o Claude? Troque uma linha no `.env`: `PROVEDOR_LLM=claude`.

Abra **http://localhost:8000/docs** — documentação interativa gerada
automaticamente pelo FastAPI a partir dos *type hints*.

### Docker

```bash
docker compose up --build
```

Sobe a API + PostgreSQL + Redis.

## 📡 API

| Método | Rota | Descrição |
|---|---|---|
| `POST` | `/datasets` | Envia um CSV → roda o pipeline → devolve `dataset_id` + perfil |
| `GET` | `/datasets/{id}` | Perfil semântico das colunas |
| `POST` | `/datasets/{id}/perguntar` | Conversa com os dados (LLM + Tool Use) |
| `GET` | `/saude` | Health check |

## 🧪 Testes

```bash
pytest -q      # 39 testes
```

Cobrem os caminhos felizes **e** os de erro: arquivo inexistente, CSV vazio,
encoding latin-1, heurística de tipo, correlação, baseline de ML (o modelo
**tem** que superar o "chute na média"), SHAP apontando a variável causal, o
loop agêntico com cliente mockado, e a API inteira.

## 🛠️ Stack

Python 3.12 · FastAPI · pandas · NumPy · scikit-learn · SHAP · **Gemini / Claude
(Tool Use)** · Pytest · Docker · PostgreSQL · Redis · GitHub Actions

## 🔌 Provedor de LLM intercambiável

O sistema roda com **Gemini** (free tier) ou **Claude** — e trocar entre eles é
mudar **uma linha do `.env`**, sem tocar em nenhuma linha de código:

```
PROVEDOR_LLM=gemini    # ou claude
```

Isso é possível porque o orquestrador ([app/llm/orchestrator.py](app/llm/orchestrator.py))
**não importa nenhum SDK**. Ele depende só de um `Protocol` (uma interface). Um
**Adapter** ([app/llm/gemini.py](app/llm/gemini.py)) traduz o dialeto do Gemini,
e uma **Factory** ([app/llm/factory.py](app/llm/factory.py)) decide quem entregar.

> Padrões: **Adapter** + **Factory** + **Dependency Inversion** (o "D" do SOLID).
> Programar contra a interface, não contra a implementação.

## 📌 Decisões técnicas notáveis

- **Anti–data leakage:** o `Pipeline` do scikit-learn garante que tudo que
  "aprende" com os dados (mediana da imputação, categorias do one-hot) seja
  aprendido **só no treino**.
- **Baseline obrigatório:** um teste **falha** se o melhor modelo não superar um
  `DummyRegressor` que chuta a média. Modelo que não bate o burro é inútil.
- **Identificadores fora do ML:** `cliente_id` é descartado das features — um ID
  não tem poder preditivo, só ensina o modelo a decorar (overfitting).
- **Mediana > média** na imputação: robusta a outliers.
- **Fail-fast + exceções próprias:** `ErroDeIngestao` encapsula o pandas; trocar
  a biblioteca não quebra quem chama.
- **Limite de upload:** protege a RAM do servidor.

## 🗺️ Próximos passos

- [ ] Persistência real (PostgreSQL) no lugar do repositório em memória
- [ ] Treino assíncrono com Celery + Redis (hoje é síncrono)
- [ ] Gráficos interativos (Plotly) e relatório em HTML/PDF
- [ ] Séries temporais (Prophet/statsmodels) para sazonalidade
- [ ] Autenticação e rate limiting
